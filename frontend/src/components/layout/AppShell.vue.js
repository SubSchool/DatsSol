import { computed, onMounted } from 'vue';
import { RouterLink, RouterView, useRoute } from 'vue-router';
import Tag from 'primevue/tag';
import { useCommandCenterStore } from '@/stores/commandCenter';
const store = useCommandCenterStore();
const route = useRoute();
const statusSeverity = computed(() => {
    if (store.runtime?.status === 'running')
        return 'success';
    if (store.runtime?.status === 'error')
        return 'danger';
    return 'warn';
});
const submitModeSeverity = computed(() => {
    if (store.runtime?.submit_mode === 'live')
        return 'danger';
    if (store.runtime?.submit_mode === 'dry-run')
        return 'info';
    return 'secondary';
});
onMounted(() => {
    void store.bootstrap();
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "app-shell" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.header, __VLS_intrinsicElements.header)({
    ...{ class: "app-header" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "brand-block" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
    ...{ class: "eyebrow" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.h1, __VLS_intrinsicElements.h1)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
    ...{ class: "subhead" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "header-meta" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "meta-chip" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "meta-label" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
(__VLS_ctx.store.runtime?.provider_label ?? 'Booting');
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "meta-chip" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "meta-label" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
(__VLS_ctx.store.runtime?.current_turn ?? 0);
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "meta-chip" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "meta-label" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
(__VLS_ctx.store.runtime?.active_strategy_key ?? 'frontier');
const __VLS_0 = {}.Tag;
/** @type {[typeof __VLS_components.Tag, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    rounded: true,
    severity: (__VLS_ctx.statusSeverity),
    value: (__VLS_ctx.store.runtime?.status ?? 'booting'),
}));
const __VLS_2 = __VLS_1({
    rounded: true,
    severity: (__VLS_ctx.statusSeverity),
    value: (__VLS_ctx.store.runtime?.status ?? 'booting'),
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
const __VLS_4 = {}.Tag;
/** @type {[typeof __VLS_components.Tag, ]} */ ;
// @ts-ignore
const __VLS_5 = __VLS_asFunctionalComponent(__VLS_4, new __VLS_4({
    rounded: true,
    severity: (__VLS_ctx.submitModeSeverity),
    value: (__VLS_ctx.store.runtime?.submit_mode ?? 'mock'),
}));
const __VLS_6 = __VLS_5({
    rounded: true,
    severity: (__VLS_ctx.submitModeSeverity),
    value: (__VLS_ctx.store.runtime?.submit_mode ?? 'mock'),
}, ...__VLS_functionalComponentArgsRest(__VLS_5));
if (__VLS_ctx.store.runtime?.provider_status?.message) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "provider-banner" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    (__VLS_ctx.store.runtime.provider_status.message);
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.nav, __VLS_intrinsicElements.nav)({
    ...{ class: "main-nav" },
});
const __VLS_8 = {}.RouterLink;
/** @type {[typeof __VLS_components.RouterLink, typeof __VLS_components.RouterLink, ]} */ ;
// @ts-ignore
const __VLS_9 = __VLS_asFunctionalComponent(__VLS_8, new __VLS_8({
    to: "/visualization",
    ...{ class: "nav-link" },
    ...{ class: ({ active: __VLS_ctx.route.path.startsWith('/visualization') }) },
}));
const __VLS_10 = __VLS_9({
    to: "/visualization",
    ...{ class: "nav-link" },
    ...{ class: ({ active: __VLS_ctx.route.path.startsWith('/visualization') }) },
}, ...__VLS_functionalComponentArgsRest(__VLS_9));
__VLS_11.slots.default;
var __VLS_11;
const __VLS_12 = {}.RouterLink;
/** @type {[typeof __VLS_components.RouterLink, typeof __VLS_components.RouterLink, ]} */ ;
// @ts-ignore
const __VLS_13 = __VLS_asFunctionalComponent(__VLS_12, new __VLS_12({
    to: "/logs",
    ...{ class: "nav-link" },
    ...{ class: ({ active: __VLS_ctx.route.path.startsWith('/logs') }) },
}));
const __VLS_14 = __VLS_13({
    to: "/logs",
    ...{ class: "nav-link" },
    ...{ class: ({ active: __VLS_ctx.route.path.startsWith('/logs') }) },
}, ...__VLS_functionalComponentArgsRest(__VLS_13));
__VLS_15.slots.default;
var __VLS_15;
__VLS_asFunctionalElement(__VLS_intrinsicElements.main, __VLS_intrinsicElements.main)({
    ...{ class: "app-main" },
});
const __VLS_16 = {}.RouterView;
/** @type {[typeof __VLS_components.RouterView, ]} */ ;
// @ts-ignore
const __VLS_17 = __VLS_asFunctionalComponent(__VLS_16, new __VLS_16({}));
const __VLS_18 = __VLS_17({}, ...__VLS_functionalComponentArgsRest(__VLS_17));
/** @type {__VLS_StyleScopedClasses['app-shell']} */ ;
/** @type {__VLS_StyleScopedClasses['app-header']} */ ;
/** @type {__VLS_StyleScopedClasses['brand-block']} */ ;
/** @type {__VLS_StyleScopedClasses['eyebrow']} */ ;
/** @type {__VLS_StyleScopedClasses['subhead']} */ ;
/** @type {__VLS_StyleScopedClasses['header-meta']} */ ;
/** @type {__VLS_StyleScopedClasses['meta-chip']} */ ;
/** @type {__VLS_StyleScopedClasses['meta-label']} */ ;
/** @type {__VLS_StyleScopedClasses['meta-chip']} */ ;
/** @type {__VLS_StyleScopedClasses['meta-label']} */ ;
/** @type {__VLS_StyleScopedClasses['meta-chip']} */ ;
/** @type {__VLS_StyleScopedClasses['meta-label']} */ ;
/** @type {__VLS_StyleScopedClasses['provider-banner']} */ ;
/** @type {__VLS_StyleScopedClasses['main-nav']} */ ;
/** @type {__VLS_StyleScopedClasses['nav-link']} */ ;
/** @type {__VLS_StyleScopedClasses['nav-link']} */ ;
/** @type {__VLS_StyleScopedClasses['app-main']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            RouterLink: RouterLink,
            RouterView: RouterView,
            Tag: Tag,
            store: store,
            route: route,
            statusSeverity: statusSeverity,
            submitModeSeverity: submitModeSeverity,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
