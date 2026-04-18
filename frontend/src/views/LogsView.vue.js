import { onMounted, ref } from 'vue';
import ApiTraceTable from '@/components/logs/ApiTraceTable.vue';
import LogsTable from '@/components/logs/LogsTable.vue';
import ServerLogsPanel from '@/components/logs/ServerLogsPanel.vue';
import { useCommandCenterStore } from '@/stores/commandCenter';
const store = useCommandCenterStore();
const activeTab = ref('planner');
onMounted(() => {
    if (store.logs.length === 0 && store.apiLogs.length === 0) {
        void Promise.all([store.fetchLogs(), store.fetchApiLogs(), store.fetchServerLogs()]);
    }
});
function refresh(filters) {
    void store.fetchLogs(filters);
}
function refreshApi(filters) {
    void store.fetchApiLogs(filters);
}
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.section, __VLS_intrinsicElements.section)({
    ...{ class: "logs-grid" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "logs-primary" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "log-tab-nav" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.activeTab = 'planner';
        } },
    type: "button",
    ...{ class: "log-tab-button" },
    ...{ class: ({ 'log-tab-button--active': __VLS_ctx.activeTab === 'planner' }) },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
    ...{ onClick: (...[$event]) => {
            __VLS_ctx.activeTab = 'api';
        } },
    type: "button",
    ...{ class: "log-tab-button" },
    ...{ class: ({ 'log-tab-button--active': __VLS_ctx.activeTab === 'api' }) },
});
if (__VLS_ctx.activeTab === 'planner') {
    /** @type {[typeof LogsTable, ]} */ ;
    // @ts-ignore
    const __VLS_0 = __VLS_asFunctionalComponent(LogsTable, new LogsTable({
        ...{ 'onRefresh': {} },
        ...{ 'onExport': {} },
        items: (__VLS_ctx.store.logs),
        total: (__VLS_ctx.store.logTotal),
        loading: (__VLS_ctx.store.logsLoading),
        filters: (__VLS_ctx.store.logFilters),
    }));
    const __VLS_1 = __VLS_0({
        ...{ 'onRefresh': {} },
        ...{ 'onExport': {} },
        items: (__VLS_ctx.store.logs),
        total: (__VLS_ctx.store.logTotal),
        loading: (__VLS_ctx.store.logsLoading),
        filters: (__VLS_ctx.store.logFilters),
    }, ...__VLS_functionalComponentArgsRest(__VLS_0));
    let __VLS_3;
    let __VLS_4;
    let __VLS_5;
    const __VLS_6 = {
        onRefresh: (__VLS_ctx.refresh)
    };
    const __VLS_7 = {
        onExport: (...[$event]) => {
            if (!(__VLS_ctx.activeTab === 'planner'))
                return;
            __VLS_ctx.store.exportLogs();
        }
    };
    var __VLS_2;
}
else {
    /** @type {[typeof ApiTraceTable, ]} */ ;
    // @ts-ignore
    const __VLS_8 = __VLS_asFunctionalComponent(ApiTraceTable, new ApiTraceTable({
        ...{ 'onRefresh': {} },
        ...{ 'onExport': {} },
        items: (__VLS_ctx.store.apiLogs),
        total: (__VLS_ctx.store.apiLogTotal),
        loading: (__VLS_ctx.store.apiLogsLoading),
        filters: (__VLS_ctx.store.apiLogFilters),
    }));
    const __VLS_9 = __VLS_8({
        ...{ 'onRefresh': {} },
        ...{ 'onExport': {} },
        items: (__VLS_ctx.store.apiLogs),
        total: (__VLS_ctx.store.apiLogTotal),
        loading: (__VLS_ctx.store.apiLogsLoading),
        filters: (__VLS_ctx.store.apiLogFilters),
    }, ...__VLS_functionalComponentArgsRest(__VLS_8));
    let __VLS_11;
    let __VLS_12;
    let __VLS_13;
    const __VLS_14 = {
        onRefresh: (__VLS_ctx.refreshApi)
    };
    const __VLS_15 = {
        onExport: (...[$event]) => {
            if (!!(__VLS_ctx.activeTab === 'planner'))
                return;
            __VLS_ctx.store.exportApiLogs();
        }
    };
    var __VLS_10;
}
/** @type {[typeof ServerLogsPanel, ]} */ ;
// @ts-ignore
const __VLS_16 = __VLS_asFunctionalComponent(ServerLogsPanel, new ServerLogsPanel({
    items: (__VLS_ctx.store.serverLogs),
}));
const __VLS_17 = __VLS_16({
    items: (__VLS_ctx.store.serverLogs),
}, ...__VLS_functionalComponentArgsRest(__VLS_16));
/** @type {__VLS_StyleScopedClasses['logs-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['logs-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['log-tab-nav']} */ ;
/** @type {__VLS_StyleScopedClasses['log-tab-button']} */ ;
/** @type {__VLS_StyleScopedClasses['log-tab-button']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            ApiTraceTable: ApiTraceTable,
            LogsTable: LogsTable,
            ServerLogsPanel: ServerLogsPanel,
            store: store,
            activeTab: activeTab,
            refresh: refresh,
            refreshApi: refreshApi,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
