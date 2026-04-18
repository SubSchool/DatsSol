import { reactive, watch } from 'vue';
import Button from 'primevue/button';
import Card from 'primevue/card';
import Column from 'primevue/column';
import DataTable from 'primevue/datatable';
import InputNumber from 'primevue/inputnumber';
import InputText from 'primevue/inputtext';
import Select from 'primevue/select';
import Tag from 'primevue/tag';
const props = defineProps();
const emit = defineEmits();
const localFilters = reactive({ ...props.filters });
watch(() => props.filters, (value) => Object.assign(localFilters, value), { deep: true });
const levelOptions = [
    { label: 'Все уровни', value: '' },
    { label: 'Info', value: 'info' },
    { label: 'Warn', value: 'warn' },
    { label: 'Error', value: 'error' },
];
const sourceOptions = [
    { label: 'Все endpoints', value: '' },
    { label: 'arena', value: 'arena' },
    { label: 'command', value: 'command' },
];
function severity(level) {
    if (level === 'error')
        return 'danger';
    if (level === 'warn')
        return 'warn';
    if (level === 'info')
        return 'info';
    return 'secondary';
}
function requestPreview(item) {
    return JSON.stringify((item.payload?.request ?? {}), null, 2);
}
function responsePreview(item) {
    if (item.payload?.response) {
        return JSON.stringify(item.payload.response, null, 2);
    }
    if (item.payload?.error) {
        return String(item.payload.error);
    }
    return '{}';
}
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
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "filters-toolbar" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "toolbar-grid toolbar-grid--api" },
    });
    const __VLS_5 = {}.Select;
    /** @type {[typeof __VLS_components.Select, ]} */ ;
    // @ts-ignore
    const __VLS_6 = __VLS_asFunctionalComponent(__VLS_5, new __VLS_5({
        modelValue: (__VLS_ctx.localFilters.level),
        options: (__VLS_ctx.levelOptions),
        optionLabel: "label",
        optionValue: "value",
        placeholder: "Уровень",
    }));
    const __VLS_7 = __VLS_6({
        modelValue: (__VLS_ctx.localFilters.level),
        options: (__VLS_ctx.levelOptions),
        optionLabel: "label",
        optionValue: "value",
        placeholder: "Уровень",
    }, ...__VLS_functionalComponentArgsRest(__VLS_6));
    const __VLS_9 = {}.Select;
    /** @type {[typeof __VLS_components.Select, ]} */ ;
    // @ts-ignore
    const __VLS_10 = __VLS_asFunctionalComponent(__VLS_9, new __VLS_9({
        modelValue: (__VLS_ctx.localFilters.source),
        options: (__VLS_ctx.sourceOptions),
        optionLabel: "label",
        optionValue: "value",
        placeholder: "Endpoint",
    }));
    const __VLS_11 = __VLS_10({
        modelValue: (__VLS_ctx.localFilters.source),
        options: (__VLS_ctx.sourceOptions),
        optionLabel: "label",
        optionValue: "value",
        placeholder: "Endpoint",
    }, ...__VLS_functionalComponentArgsRest(__VLS_10));
    const __VLS_13 = {}.InputText;
    /** @type {[typeof __VLS_components.InputText, ]} */ ;
    // @ts-ignore
    const __VLS_14 = __VLS_asFunctionalComponent(__VLS_13, new __VLS_13({
        modelValue: (__VLS_ctx.localFilters.search),
        placeholder: "Поиск по endpoint / payload",
    }));
    const __VLS_15 = __VLS_14({
        modelValue: (__VLS_ctx.localFilters.search),
        placeholder: "Поиск по endpoint / payload",
    }, ...__VLS_functionalComponentArgsRest(__VLS_14));
    const __VLS_17 = {}.InputNumber;
    /** @type {[typeof __VLS_components.InputNumber, ]} */ ;
    // @ts-ignore
    const __VLS_18 = __VLS_asFunctionalComponent(__VLS_17, new __VLS_17({
        modelValue: (__VLS_ctx.localFilters.tickFrom),
        placeholder: "Ход от",
    }));
    const __VLS_19 = __VLS_18({
        modelValue: (__VLS_ctx.localFilters.tickFrom),
        placeholder: "Ход от",
    }, ...__VLS_functionalComponentArgsRest(__VLS_18));
    const __VLS_21 = {}.InputNumber;
    /** @type {[typeof __VLS_components.InputNumber, ]} */ ;
    // @ts-ignore
    const __VLS_22 = __VLS_asFunctionalComponent(__VLS_21, new __VLS_21({
        modelValue: (__VLS_ctx.localFilters.tickTo),
        placeholder: "Ход до",
    }));
    const __VLS_23 = __VLS_22({
        modelValue: (__VLS_ctx.localFilters.tickTo),
        placeholder: "Ход до",
    }, ...__VLS_functionalComponentArgsRest(__VLS_22));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "filters-actions" },
    });
    const __VLS_25 = {}.Button;
    /** @type {[typeof __VLS_components.Button, ]} */ ;
    // @ts-ignore
    const __VLS_26 = __VLS_asFunctionalComponent(__VLS_25, new __VLS_25({
        ...{ 'onClick': {} },
        icon: "pi pi-filter",
        label: "Применить",
    }));
    const __VLS_27 = __VLS_26({
        ...{ 'onClick': {} },
        icon: "pi pi-filter",
        label: "Применить",
    }, ...__VLS_functionalComponentArgsRest(__VLS_26));
    let __VLS_29;
    let __VLS_30;
    let __VLS_31;
    const __VLS_32 = {
        onClick: (...[$event]) => {
            __VLS_ctx.emit('refresh', { ...__VLS_ctx.localFilters, category: 'api' });
        }
    };
    var __VLS_28;
    const __VLS_33 = {}.Button;
    /** @type {[typeof __VLS_components.Button, ]} */ ;
    // @ts-ignore
    const __VLS_34 = __VLS_asFunctionalComponent(__VLS_33, new __VLS_33({
        ...{ 'onClick': {} },
        icon: "pi pi-download",
        label: "CSV",
        severity: "secondary",
    }));
    const __VLS_35 = __VLS_34({
        ...{ 'onClick': {} },
        icon: "pi pi-download",
        label: "CSV",
        severity: "secondary",
    }, ...__VLS_functionalComponentArgsRest(__VLS_34));
    let __VLS_37;
    let __VLS_38;
    let __VLS_39;
    const __VLS_40 = {
        onClick: (...[$event]) => {
            __VLS_ctx.emit('export');
        }
    };
    var __VLS_36;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "table-meta" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    (__VLS_ctx.total);
    const __VLS_41 = {}.DataTable;
    /** @type {[typeof __VLS_components.DataTable, typeof __VLS_components.DataTable, ]} */ ;
    // @ts-ignore
    const __VLS_42 = __VLS_asFunctionalComponent(__VLS_41, new __VLS_41({
        value: (__VLS_ctx.items),
        loading: (__VLS_ctx.loading),
        scrollable: true,
        scrollHeight: "72vh",
        stripedRows: true,
        showGridlines: true,
        dataKey: "id",
    }));
    const __VLS_43 = __VLS_42({
        value: (__VLS_ctx.items),
        loading: (__VLS_ctx.loading),
        scrollable: true,
        scrollHeight: "72vh",
        stripedRows: true,
        showGridlines: true,
        dataKey: "id",
    }, ...__VLS_functionalComponentArgsRest(__VLS_42));
    __VLS_44.slots.default;
    const __VLS_45 = {}.Column;
    /** @type {[typeof __VLS_components.Column, typeof __VLS_components.Column, ]} */ ;
    // @ts-ignore
    const __VLS_46 = __VLS_asFunctionalComponent(__VLS_45, new __VLS_45({
        field: "created_at",
        header: "Время",
        ...{ style: {} },
    }));
    const __VLS_47 = __VLS_46({
        field: "created_at",
        header: "Время",
        ...{ style: {} },
    }, ...__VLS_functionalComponentArgsRest(__VLS_46));
    __VLS_48.slots.default;
    {
        const { body: __VLS_thisSlot } = __VLS_48.slots;
        const [{ data }] = __VLS_getSlotParams(__VLS_thisSlot);
        (new Date(data.created_at).toLocaleString());
    }
    var __VLS_48;
    const __VLS_49 = {}.Column;
    /** @type {[typeof __VLS_components.Column, ]} */ ;
    // @ts-ignore
    const __VLS_50 = __VLS_asFunctionalComponent(__VLS_49, new __VLS_49({
        field: "turn_number",
        header: "Ход",
        ...{ style: {} },
    }));
    const __VLS_51 = __VLS_50({
        field: "turn_number",
        header: "Ход",
        ...{ style: {} },
    }, ...__VLS_functionalComponentArgsRest(__VLS_50));
    const __VLS_53 = {}.Column;
    /** @type {[typeof __VLS_components.Column, typeof __VLS_components.Column, ]} */ ;
    // @ts-ignore
    const __VLS_54 = __VLS_asFunctionalComponent(__VLS_53, new __VLS_53({
        field: "level",
        header: "Level",
        ...{ style: {} },
    }));
    const __VLS_55 = __VLS_54({
        field: "level",
        header: "Level",
        ...{ style: {} },
    }, ...__VLS_functionalComponentArgsRest(__VLS_54));
    __VLS_56.slots.default;
    {
        const { body: __VLS_thisSlot } = __VLS_56.slots;
        const [{ data }] = __VLS_getSlotParams(__VLS_thisSlot);
        const __VLS_57 = {}.Tag;
        /** @type {[typeof __VLS_components.Tag, ]} */ ;
        // @ts-ignore
        const __VLS_58 = __VLS_asFunctionalComponent(__VLS_57, new __VLS_57({
            severity: (__VLS_ctx.severity(data.level)),
            value: (data.level),
        }));
        const __VLS_59 = __VLS_58({
            severity: (__VLS_ctx.severity(data.level)),
            value: (data.level),
        }, ...__VLS_functionalComponentArgsRest(__VLS_58));
    }
    var __VLS_56;
    const __VLS_61 = {}.Column;
    /** @type {[typeof __VLS_components.Column, ]} */ ;
    // @ts-ignore
    const __VLS_62 = __VLS_asFunctionalComponent(__VLS_61, new __VLS_61({
        field: "source",
        header: "Source",
        ...{ style: {} },
    }));
    const __VLS_63 = __VLS_62({
        field: "source",
        header: "Source",
        ...{ style: {} },
    }, ...__VLS_functionalComponentArgsRest(__VLS_62));
    const __VLS_65 = {}.Column;
    /** @type {[typeof __VLS_components.Column, ]} */ ;
    // @ts-ignore
    const __VLS_66 = __VLS_asFunctionalComponent(__VLS_65, new __VLS_65({
        field: "message",
        header: "Endpoint",
        ...{ style: {} },
    }));
    const __VLS_67 = __VLS_66({
        field: "message",
        header: "Endpoint",
        ...{ style: {} },
    }, ...__VLS_functionalComponentArgsRest(__VLS_66));
    const __VLS_69 = {}.Column;
    /** @type {[typeof __VLS_components.Column, typeof __VLS_components.Column, ]} */ ;
    // @ts-ignore
    const __VLS_70 = __VLS_asFunctionalComponent(__VLS_69, new __VLS_69({
        header: "Request",
        ...{ style: {} },
    }));
    const __VLS_71 = __VLS_70({
        header: "Request",
        ...{ style: {} },
    }, ...__VLS_functionalComponentArgsRest(__VLS_70));
    __VLS_72.slots.default;
    {
        const { body: __VLS_thisSlot } = __VLS_72.slots;
        const [{ data }] = __VLS_getSlotParams(__VLS_thisSlot);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.pre, __VLS_intrinsicElements.pre)({
            ...{ class: "payload-preview" },
        });
        (__VLS_ctx.requestPreview(data));
    }
    var __VLS_72;
    const __VLS_73 = {}.Column;
    /** @type {[typeof __VLS_components.Column, typeof __VLS_components.Column, ]} */ ;
    // @ts-ignore
    const __VLS_74 = __VLS_asFunctionalComponent(__VLS_73, new __VLS_73({
        header: "Response / Error",
        ...{ style: {} },
    }));
    const __VLS_75 = __VLS_74({
        header: "Response / Error",
        ...{ style: {} },
    }, ...__VLS_functionalComponentArgsRest(__VLS_74));
    __VLS_76.slots.default;
    {
        const { body: __VLS_thisSlot } = __VLS_76.slots;
        const [{ data }] = __VLS_getSlotParams(__VLS_thisSlot);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.pre, __VLS_intrinsicElements.pre)({
            ...{ class: "payload-preview" },
        });
        (__VLS_ctx.responsePreview(data));
    }
    var __VLS_76;
    var __VLS_44;
}
var __VLS_3;
/** @type {__VLS_StyleScopedClasses['panel-card']} */ ;
/** @type {__VLS_StyleScopedClasses['filters-toolbar']} */ ;
/** @type {__VLS_StyleScopedClasses['toolbar-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['toolbar-grid--api']} */ ;
/** @type {__VLS_StyleScopedClasses['filters-actions']} */ ;
/** @type {__VLS_StyleScopedClasses['table-meta']} */ ;
/** @type {__VLS_StyleScopedClasses['payload-preview']} */ ;
/** @type {__VLS_StyleScopedClasses['payload-preview']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            Button: Button,
            Card: Card,
            Column: Column,
            DataTable: DataTable,
            InputNumber: InputNumber,
            InputText: InputText,
            Select: Select,
            Tag: Tag,
            emit: emit,
            localFilters: localFilters,
            levelOptions: levelOptions,
            sourceOptions: sourceOptions,
            severity: severity,
            requestPreview: requestPreview,
            responsePreview: responsePreview,
        };
    },
    __typeEmits: {},
    __typeProps: {},
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    __typeEmits: {},
    __typeProps: {},
});
; /* PartiallyEnd: #4569/main.vue */
