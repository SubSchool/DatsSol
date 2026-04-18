import Card from 'primevue/card';
import Column from 'primevue/column';
import DataTable from 'primevue/datatable';
const __VLS_props = defineProps();
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
const __VLS_0 = {}.Card;
/** @type {[typeof __VLS_components.Card, typeof __VLS_components.Card, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    ...{ class: "panel-card" },
}));
const __VLS_2 = __VLS_1({
    ...{ class: "panel-card" },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
var __VLS_4 = {};
__VLS_3.slots.default;
{
    const { title: __VLS_thisSlot } = __VLS_3.slots;
}
{
    const { content: __VLS_thisSlot } = __VLS_3.slots;
    const __VLS_5 = {}.DataTable;
    /** @type {[typeof __VLS_components.DataTable, typeof __VLS_components.DataTable, ]} */ ;
    // @ts-ignore
    const __VLS_6 = __VLS_asFunctionalComponent(__VLS_5, new __VLS_5({
        value: (__VLS_ctx.items),
        scrollable: true,
        scrollHeight: "72vh",
        stripedRows: true,
        showGridlines: true,
    }));
    const __VLS_7 = __VLS_6({
        value: (__VLS_ctx.items),
        scrollable: true,
        scrollHeight: "72vh",
        stripedRows: true,
        showGridlines: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_6));
    __VLS_8.slots.default;
    const __VLS_9 = {}.Column;
    /** @type {[typeof __VLS_components.Column, ]} */ ;
    // @ts-ignore
    const __VLS_10 = __VLS_asFunctionalComponent(__VLS_9, new __VLS_9({
        field: "time",
        header: "Время",
        ...{ style: {} },
    }));
    const __VLS_11 = __VLS_10({
        field: "time",
        header: "Время",
        ...{ style: {} },
    }, ...__VLS_functionalComponentArgsRest(__VLS_10));
    const __VLS_13 = {}.Column;
    /** @type {[typeof __VLS_components.Column, ]} */ ;
    // @ts-ignore
    const __VLS_14 = __VLS_asFunctionalComponent(__VLS_13, new __VLS_13({
        field: "message",
        header: "Сообщение",
        ...{ style: {} },
    }));
    const __VLS_15 = __VLS_14({
        field: "message",
        header: "Сообщение",
        ...{ style: {} },
    }, ...__VLS_functionalComponentArgsRest(__VLS_14));
    var __VLS_8;
}
var __VLS_3;
/** @type {__VLS_StyleScopedClasses['panel-card']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            Card: Card,
            Column: Column,
            DataTable: DataTable,
        };
    },
    __typeProps: {},
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    __typeProps: {},
});
; /* PartiallyEnd: #4569/main.vue */
