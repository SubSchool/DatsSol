import { defineStore } from 'pinia';
import { api } from '@/api/client';
let telemetrySocket = null;
let reconnectTimer = null;
let fallbackPollTimer = null;
function websocketUrl() {
    if (import.meta.env.VITE_WS_BASE_URL) {
        return import.meta.env.VITE_WS_BASE_URL;
    }
    const url = new URL(window.location.href);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    url.pathname = '/ws/telemetry';
    url.search = '';
    url.hash = '';
    return url.toString();
}
export const useCommandCenterStore = defineStore('command-center', {
    state: () => ({
        runtime: null,
        world: null,
        logs: [],
        logTotal: 0,
        apiLogs: [],
        apiLogTotal: 0,
        serverLogs: [],
        serverLogTotal: 0,
        logsLoading: false,
        apiLogsLoading: false,
        bootstrapping: false,
        logFilters: {
            level: '',
            category: '',
            source: '',
            search: '',
            tickFrom: null,
            tickTo: null,
        },
        apiLogFilters: {
            level: '',
            category: 'api',
            source: '',
            search: '',
            tickFrom: null,
            tickTo: null,
        },
    }),
    getters: {
        selectedProviderLabel(state) {
            return state.runtime?.provider_label ?? 'DatsSol';
        },
    },
    actions: {
        scheduleReconnect() {
            if (reconnectTimer !== null) {
                return;
            }
            reconnectTimer = window.setTimeout(() => {
                reconnectTimer = null;
                this.connectTelemetry();
            }, 1250);
        },
        ensureFallbackPolling() {
            if (fallbackPollTimer !== null) {
                return;
            }
            fallbackPollTimer = window.setInterval(async () => {
                if (this.bootstrapping)
                    return;
                const socketOpen = telemetrySocket?.readyState === WebSocket.OPEN;
                const worldAgeMs = this.world?.updated_at ? Date.now() - new Date(this.world.updated_at).getTime() : Number.POSITIVE_INFINITY;
                if (socketOpen && worldAgeMs < 2400) {
                    return;
                }
                try {
                    await Promise.all([this.fetchRuntime(), this.fetchWorld()]);
                }
                catch {
                    // Fallback polling is best-effort. The live websocket path remains primary.
                }
            }, 1200);
        },
        async bootstrap() {
            if (this.bootstrapping)
                return;
            this.bootstrapping = true;
            await Promise.all([this.fetchRuntime(), this.fetchWorld(), this.fetchLogs(), this.fetchApiLogs(), this.fetchServerLogs()]);
            this.connectTelemetry();
            this.ensureFallbackPolling();
            this.bootstrapping = false;
        },
        connectTelemetry() {
            if (telemetrySocket && telemetrySocket.readyState <= WebSocket.OPEN) {
                return;
            }
            telemetrySocket?.close();
            telemetrySocket = new WebSocket(websocketUrl());
            telemetrySocket.onopen = () => {
                if (reconnectTimer !== null) {
                    window.clearTimeout(reconnectTimer);
                    reconnectTimer = null;
                }
            };
            telemetrySocket.onmessage = (event) => {
                const payload = JSON.parse(event.data);
                if (payload.type === 'world.updated') {
                    this.world = payload.world;
                    this.serverLogs = (payload.world?.server_logs ?? []);
                    this.serverLogTotal = this.serverLogs.length;
                }
                if (payload.type === 'runtime.updated') {
                    this.runtime = payload.runtime;
                }
            };
            telemetrySocket.onerror = () => {
                telemetrySocket?.close();
            };
            telemetrySocket.onclose = () => {
                telemetrySocket = null;
                this.scheduleReconnect();
            };
        },
        async fetchRuntime() {
            const { data } = await api.get('/runtime');
            this.runtime = data;
        },
        async fetchWorld() {
            const { data } = await api.get('/world');
            this.world = data;
        },
        async fetchServerLogs() {
            const { data } = await api.get('/server-logs');
            this.serverLogs = data.items;
            this.serverLogTotal = data.total;
        },
        async fetchLogs(partial) {
            this.logsLoading = true;
            if (partial) {
                this.logFilters = { ...this.logFilters, ...partial };
            }
            const { data } = await api.get('/logs', {
                params: {
                    level: this.logFilters.level || undefined,
                    category: this.logFilters.category || undefined,
                    source: this.logFilters.source || undefined,
                    search: this.logFilters.search || undefined,
                    tick_from: this.logFilters.tickFrom ?? undefined,
                    tick_to: this.logFilters.tickTo ?? undefined,
                    limit: 500,
                },
            });
            this.logs = data.items;
            this.logTotal = data.total;
            this.logsLoading = false;
        },
        async fetchApiLogs(partial) {
            this.apiLogsLoading = true;
            if (partial) {
                this.apiLogFilters = { ...this.apiLogFilters, ...partial, category: 'api' };
            }
            const { data } = await api.get('/logs', {
                params: {
                    level: this.apiLogFilters.level || undefined,
                    category: 'api',
                    source: this.apiLogFilters.source || undefined,
                    search: this.apiLogFilters.search || undefined,
                    tick_from: this.apiLogFilters.tickFrom ?? undefined,
                    tick_to: this.apiLogFilters.tickTo ?? undefined,
                    limit: 500,
                },
            });
            this.apiLogs = data.items;
            this.apiLogTotal = data.total;
            this.apiLogsLoading = false;
        },
        async startRuntime() {
            const { data } = await api.post('/runtime/start');
            this.runtime = data;
        },
        async stopRuntime() {
            const { data } = await api.post('/runtime/stop');
            this.runtime = data;
        },
        async restartRuntime() {
            const { data } = await api.post('/runtime/restart');
            this.runtime = data;
            await Promise.all([this.fetchWorld(), this.fetchLogs(), this.fetchApiLogs(), this.fetchServerLogs()]);
        },
        async tickOnce() {
            const { data } = await api.post('/runtime/tick');
            this.runtime = data;
            await Promise.all([this.fetchWorld(), this.fetchLogs(), this.fetchApiLogs(), this.fetchServerLogs()]);
        },
        async setStrategy(strategyKey) {
            const { data } = await api.post('/runtime/strategy', {
                strategy_key: strategyKey,
            });
            this.runtime = data;
        },
        async updateWeights(weights) {
            const { data } = await api.post('/runtime/weights', weights);
            this.runtime = data;
        },
        async setProvider(providerKey) {
            const { data } = await api.post('/runtime/provider', {
                provider_key: providerKey,
            });
            this.runtime = data;
            await Promise.all([this.fetchWorld(), this.fetchServerLogs()]);
        },
        async setSubmitMode(submitMode) {
            const { data } = await api.post('/runtime/submit-mode', {
                submit_mode: submitMode,
            });
            this.runtime = data;
        },
        async createDirective(payload) {
            await api.post('/world/directives', payload);
            await Promise.all([this.fetchWorld(), this.fetchLogs()]);
        },
        async exportLogs(filters, filename = 'dats-sol-logs.csv') {
            const appliedFilters = filters ?? this.logFilters;
            const response = await api.get('/logs/export', {
                params: {
                    level: appliedFilters.level || undefined,
                    category: appliedFilters.category || undefined,
                    source: appliedFilters.source || undefined,
                    search: appliedFilters.search || undefined,
                    tick_from: appliedFilters.tickFrom ?? undefined,
                    tick_to: appliedFilters.tickTo ?? undefined,
                },
                responseType: 'blob',
            });
            const blobUrl = window.URL.createObjectURL(response.data);
            const anchor = document.createElement('a');
            anchor.href = blobUrl;
            anchor.download = filename;
            anchor.click();
            window.URL.revokeObjectURL(blobUrl);
        },
        async exportApiLogs() {
            await this.exportLogs(this.apiLogFilters, 'dats-sol-api-trace.csv');
        },
    },
});
