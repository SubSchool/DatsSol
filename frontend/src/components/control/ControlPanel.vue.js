import { computed, reactive, ref, watch } from 'vue';
import Button from 'primevue/button';
import Card from 'primevue/card';
import Divider from 'primevue/divider';
import InputNumber from 'primevue/inputnumber';
import Select from 'primevue/select';
import SelectButton from 'primevue/selectbutton';
import Slider from 'primevue/slider';
import Tag from 'primevue/tag';
import ToggleButton from 'primevue/togglebutton';
import { useCommandCenterStore } from '@/stores/commandCenter';
const props = defineProps();
const emit = defineEmits();
const store = useCommandCenterStore();
const strategyState = reactive({
    selectedStrategy: 'frontier',
    expansion_bias: 0.88,
    support_bias: 0.76,
    boosted_cell_bias: 0.95,
    safety_bias: 0.72,
    beaver_hunt_bias: 0.42,
    sabotage_bias: 0.28,
});
const providerKey = ref('datssol-mock');
const submitMode = ref('mock');
const forcedUpgrade = ref('');
watch(() => props.runtime, (runtime) => {
    if (!runtime)
        return;
    strategyState.selectedStrategy = runtime.active_strategy_key;
    strategyState.expansion_bias = runtime.weights.expansion_bias;
    strategyState.support_bias = runtime.weights.support_bias;
    strategyState.boosted_cell_bias = runtime.weights.boosted_cell_bias;
    strategyState.safety_bias = runtime.weights.safety_bias;
    strategyState.beaver_hunt_bias = runtime.weights.beaver_hunt_bias;
    strategyState.sabotage_bias = runtime.weights.sabotage_bias;
    providerKey.value = runtime.provider;
    submitMode.value = runtime.submit_mode;
}, { immediate: true });
watch(() => props.world?.recommended_upgrade?.name, (value) => {
    if (value)
        forcedUpgrade.value = value;
}, { immediate: true });
const commandModeModel = computed({
    get: () => props.commandMode,
    set: (value) => emit('update:commandMode', value),
});
const manualActionModel = computed({
    get: () => props.manualActionKind,
    set: (value) => emit('update:manualActionKind', value),
});
const strategyOptions = computed(() => props.runtime?.strategies.map((strategy) => ({
    label: strategy.label,
    value: strategy.key,
})) ?? []);
const providerOptions = [
    { label: 'Mock Sandbox', value: 'datssol-mock' },
    { label: 'Live API', value: 'datssol-live' },
];
const submitModeOptions = [
    { label: 'Mock', value: 'mock' },
    { label: 'Dry Run', value: 'dry-run' },
    { label: 'Live Submit', value: 'live' },
];
const manualActionOptions = [
    { label: 'Стройка', value: 'build' },
    { label: 'Ремонт', value: 'repair' },
    { label: 'Диверсия', value: 'sabotage' },
    { label: 'Бобры', value: 'beaver_attack' },
    { label: 'Перенос ЦУ', value: 'relocate_main' },
];
const upgradeOptions = computed(() => props.world?.upgrades.tiers
    .filter((tier) => tier.current < tier.max)
    .map((tier) => ({
    label: `${tier.name} (${tier.current}/${tier.max})`,
    value: tier.name,
})) ?? []);
const commandHint = computed(() => {
    if (props.manualActionKind === 'build') {
        return 'В режиме просмотра можно выделить авторов, затем перейти в command mode и кликнуть по клетке или стройке. Если авторы не выделены, planner выберет их сам.';
    }
    if (props.manualActionKind === 'repair') {
        return 'Сначала выдели плантации-исполнители в browse mode при необходимости. В command mode кликни по своей плантации, которую нужно чинить.';
    }
    if (props.manualActionKind === 'sabotage') {
        return 'В command mode кликни по вражеской плантации. Выделение авторов опционально.';
    }
    if (props.manualActionKind === 'beaver_attack') {
        return 'В command mode кликни по логову бобров. Выделение авторов опционально.';
    }
    return 'В command mode кликни по своей плантации, куда нужно перенести ЦУ. Авторы для переноса не нужны.';
});
async function applyStrategy() {
    await store.setStrategy(strategyState.selectedStrategy);
}
async function applyWeights() {
    await store.updateWeights({
        expansion_bias: strategyState.expansion_bias,
        support_bias: strategyState.support_bias,
        boosted_cell_bias: strategyState.boosted_cell_bias,
        safety_bias: strategyState.safety_bias,
        beaver_hunt_bias: strategyState.beaver_hunt_bias,
        sabotage_bias: strategyState.sabotage_bias,
    });
}
async function applyProvider() {
    await store.setProvider(providerKey.value);
}
async function applySubmitMode() {
    await store.setSubmitMode(submitMode.value);
}
async function forceUpgrade() {
    if (!forcedUpgrade.value)
        return;
    await store.createDirective({
        kind: 'upgrade',
        upgrade_name: forcedUpgrade.value,
        note: `force upgrade ${forcedUpgrade.value}`,
    });
}
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "control-panel" },
});
const __VLS_0 = {}.Card;
/** @type {[typeof __VLS_components.Card, typeof __VLS_components.Card, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    ...{ class: "panel-card control-panel-card" },
}));
const __VLS_2 = __VLS_1({
    ...{ class: "panel-card control-panel-card" },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
__VLS_3.slots.default;
{
    const { title: __VLS_thisSlot } = __VLS_3.slots;
}
{
    const { content: __VLS_thisSlot } = __VLS_3.slots;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "panel-grid" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "button-row" },
    });
    const __VLS_4 = {}.Button;
    /** @type {[typeof __VLS_components.Button, ]} */ ;
    // @ts-ignore
    const __VLS_5 = __VLS_asFunctionalComponent(__VLS_4, new __VLS_4({
        ...{ 'onClick': {} },
        icon: "pi pi-play",
        label: "Старт",
    }));
    const __VLS_6 = __VLS_5({
        ...{ 'onClick': {} },
        icon: "pi pi-play",
        label: "Старт",
    }, ...__VLS_functionalComponentArgsRest(__VLS_5));
    let __VLS_8;
    let __VLS_9;
    let __VLS_10;
    const __VLS_11 = {
        onClick: (...[$event]) => {
            __VLS_ctx.store.startRuntime();
        }
    };
    var __VLS_7;
    const __VLS_12 = {}.Button;
    /** @type {[typeof __VLS_components.Button, ]} */ ;
    // @ts-ignore
    const __VLS_13 = __VLS_asFunctionalComponent(__VLS_12, new __VLS_12({
        ...{ 'onClick': {} },
        icon: "pi pi-pause",
        severity: "secondary",
        label: "Стоп",
    }));
    const __VLS_14 = __VLS_13({
        ...{ 'onClick': {} },
        icon: "pi pi-pause",
        severity: "secondary",
        label: "Стоп",
    }, ...__VLS_functionalComponentArgsRest(__VLS_13));
    let __VLS_16;
    let __VLS_17;
    let __VLS_18;
    const __VLS_19 = {
        onClick: (...[$event]) => {
            __VLS_ctx.store.stopRuntime();
        }
    };
    var __VLS_15;
    const __VLS_20 = {}.Button;
    /** @type {[typeof __VLS_components.Button, ]} */ ;
    // @ts-ignore
    const __VLS_21 = __VLS_asFunctionalComponent(__VLS_20, new __VLS_20({
        ...{ 'onClick': {} },
        icon: "pi pi-refresh",
        severity: "contrast",
        label: "Рестарт",
    }));
    const __VLS_22 = __VLS_21({
        ...{ 'onClick': {} },
        icon: "pi pi-refresh",
        severity: "contrast",
        label: "Рестарт",
    }, ...__VLS_functionalComponentArgsRest(__VLS_21));
    let __VLS_24;
    let __VLS_25;
    let __VLS_26;
    const __VLS_27 = {
        onClick: (...[$event]) => {
            __VLS_ctx.store.restartRuntime();
        }
    };
    var __VLS_23;
    const __VLS_28 = {}.Button;
    /** @type {[typeof __VLS_components.Button, ]} */ ;
    // @ts-ignore
    const __VLS_29 = __VLS_asFunctionalComponent(__VLS_28, new __VLS_28({
        ...{ 'onClick': {} },
        icon: "pi pi-step-forward",
        severity: "help",
        label: "1 Ход",
    }));
    const __VLS_30 = __VLS_29({
        ...{ 'onClick': {} },
        icon: "pi pi-step-forward",
        severity: "help",
        label: "1 Ход",
    }, ...__VLS_functionalComponentArgsRest(__VLS_29));
    let __VLS_32;
    let __VLS_33;
    let __VLS_34;
    const __VLS_35 = {
        onClick: (...[$event]) => {
            __VLS_ctx.store.tickOnce();
        }
    };
    var __VLS_31;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "stat-grid" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "stat-item" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "stat-label" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({
        ...{ class: "stat-value" },
    });
    (__VLS_ctx.world?.plantations.length ?? 0);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "stat-item" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "stat-label" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({
        ...{ class: "stat-value" },
    });
    (__VLS_ctx.world?.stats.connected_plantations ?? 0);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "stat-item" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "stat-label" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({
        ...{ class: "stat-value" },
    });
    (__VLS_ctx.selectedPlantationIds.length);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "stat-item" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "stat-label" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({
        ...{ class: "stat-value" },
    });
    (__VLS_ctx.world?.upgrades.points ?? 0);
    const __VLS_36 = {}.Divider;
    /** @type {[typeof __VLS_components.Divider, ]} */ ;
    // @ts-ignore
    const __VLS_37 = __VLS_asFunctionalComponent(__VLS_36, new __VLS_36({}));
    const __VLS_38 = __VLS_37({}, ...__VLS_functionalComponentArgsRest(__VLS_37));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "stacked-section" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "section-header" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({
        ...{ class: "section-label" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
        ...{ class: "section-subtitle" },
    });
    (__VLS_ctx.runtime?.provider_status?.message);
    const __VLS_40 = {}.Tag;
    /** @type {[typeof __VLS_components.Tag, ]} */ ;
    // @ts-ignore
    const __VLS_41 = __VLS_asFunctionalComponent(__VLS_40, new __VLS_40({
        severity: (__VLS_ctx.runtime?.provider_status?.ready ? 'success' : 'warn'),
        value: (__VLS_ctx.runtime?.provider_status?.ready ? 'готов' : 'нужна настройка'),
    }));
    const __VLS_42 = __VLS_41({
        severity: (__VLS_ctx.runtime?.provider_status?.ready ? 'success' : 'warn'),
        value: (__VLS_ctx.runtime?.provider_status?.ready ? 'готов' : 'нужна настройка'),
    }, ...__VLS_functionalComponentArgsRest(__VLS_41));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "form-row" },
    });
    const __VLS_44 = {}.Select;
    /** @type {[typeof __VLS_components.Select, ]} */ ;
    // @ts-ignore
    const __VLS_45 = __VLS_asFunctionalComponent(__VLS_44, new __VLS_44({
        modelValue: (__VLS_ctx.providerKey),
        options: (__VLS_ctx.providerOptions),
        optionLabel: "label",
        optionValue: "value",
    }));
    const __VLS_46 = __VLS_45({
        modelValue: (__VLS_ctx.providerKey),
        options: (__VLS_ctx.providerOptions),
        optionLabel: "label",
        optionValue: "value",
    }, ...__VLS_functionalComponentArgsRest(__VLS_45));
    const __VLS_48 = {}.Button;
    /** @type {[typeof __VLS_components.Button, ]} */ ;
    // @ts-ignore
    const __VLS_49 = __VLS_asFunctionalComponent(__VLS_48, new __VLS_48({
        ...{ 'onClick': {} },
        label: "Применить",
        icon: "pi pi-send",
        severity: "secondary",
    }));
    const __VLS_50 = __VLS_49({
        ...{ 'onClick': {} },
        label: "Применить",
        icon: "pi pi-send",
        severity: "secondary",
    }, ...__VLS_functionalComponentArgsRest(__VLS_49));
    let __VLS_52;
    let __VLS_53;
    let __VLS_54;
    const __VLS_55 = {
        onClick: (__VLS_ctx.applyProvider)
    };
    var __VLS_51;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "form-row" },
    });
    const __VLS_56 = {}.Select;
    /** @type {[typeof __VLS_components.Select, ]} */ ;
    // @ts-ignore
    const __VLS_57 = __VLS_asFunctionalComponent(__VLS_56, new __VLS_56({
        modelValue: (__VLS_ctx.submitMode),
        options: (__VLS_ctx.submitModeOptions),
        optionLabel: "label",
        optionValue: "value",
    }));
    const __VLS_58 = __VLS_57({
        modelValue: (__VLS_ctx.submitMode),
        options: (__VLS_ctx.submitModeOptions),
        optionLabel: "label",
        optionValue: "value",
    }, ...__VLS_functionalComponentArgsRest(__VLS_57));
    const __VLS_60 = {}.Button;
    /** @type {[typeof __VLS_components.Button, ]} */ ;
    // @ts-ignore
    const __VLS_61 = __VLS_asFunctionalComponent(__VLS_60, new __VLS_60({
        ...{ 'onClick': {} },
        label: "Режим сабмита",
        icon: "pi pi-bolt",
        severity: "secondary",
    }));
    const __VLS_62 = __VLS_61({
        ...{ 'onClick': {} },
        label: "Режим сабмита",
        icon: "pi pi-bolt",
        severity: "secondary",
    }, ...__VLS_functionalComponentArgsRest(__VLS_61));
    let __VLS_64;
    let __VLS_65;
    let __VLS_66;
    const __VLS_67 = {
        onClick: (__VLS_ctx.applySubmitMode)
    };
    var __VLS_63;
    const __VLS_68 = {}.Divider;
    /** @type {[typeof __VLS_components.Divider, ]} */ ;
    // @ts-ignore
    const __VLS_69 = __VLS_asFunctionalComponent(__VLS_68, new __VLS_68({}));
    const __VLS_70 = __VLS_69({}, ...__VLS_functionalComponentArgsRest(__VLS_69));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "stacked-section" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({
        ...{ class: "section-label" },
    });
    const __VLS_72 = {}.SelectButton;
    /** @type {[typeof __VLS_components.SelectButton, ]} */ ;
    // @ts-ignore
    const __VLS_73 = __VLS_asFunctionalComponent(__VLS_72, new __VLS_72({
        modelValue: (__VLS_ctx.strategyState.selectedStrategy),
        options: (__VLS_ctx.strategyOptions),
        optionLabel: "label",
        optionValue: "value",
    }));
    const __VLS_74 = __VLS_73({
        modelValue: (__VLS_ctx.strategyState.selectedStrategy),
        options: (__VLS_ctx.strategyOptions),
        optionLabel: "label",
        optionValue: "value",
    }, ...__VLS_functionalComponentArgsRest(__VLS_73));
    const __VLS_76 = {}.Button;
    /** @type {[typeof __VLS_components.Button, ]} */ ;
    // @ts-ignore
    const __VLS_77 = __VLS_asFunctionalComponent(__VLS_76, new __VLS_76({
        ...{ 'onClick': {} },
        label: "Переключить стратегию",
        icon: "pi pi-compass",
    }));
    const __VLS_78 = __VLS_77({
        ...{ 'onClick': {} },
        label: "Переключить стратегию",
        icon: "pi pi-compass",
    }, ...__VLS_functionalComponentArgsRest(__VLS_77));
    let __VLS_80;
    let __VLS_81;
    let __VLS_82;
    const __VLS_83 = {
        onClick: (__VLS_ctx.applyStrategy)
    };
    var __VLS_79;
    const __VLS_84 = {}.Divider;
    /** @type {[typeof __VLS_components.Divider, ]} */ ;
    // @ts-ignore
    const __VLS_85 = __VLS_asFunctionalComponent(__VLS_84, new __VLS_84({}));
    const __VLS_86 = __VLS_85({}, ...__VLS_functionalComponentArgsRest(__VLS_85));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "stacked-section" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "section-header" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({
        ...{ class: "section-label" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
        ...{ class: "section-subtitle" },
    });
    const __VLS_88 = {}.Button;
    /** @type {[typeof __VLS_components.Button, ]} */ ;
    // @ts-ignore
    const __VLS_89 = __VLS_asFunctionalComponent(__VLS_88, new __VLS_88({
        ...{ 'onClick': {} },
        label: "Применить веса",
        icon: "pi pi-sliders-h",
        severity: "secondary",
    }));
    const __VLS_90 = __VLS_89({
        ...{ 'onClick': {} },
        label: "Применить веса",
        icon: "pi pi-sliders-h",
        severity: "secondary",
    }, ...__VLS_functionalComponentArgsRest(__VLS_89));
    let __VLS_92;
    let __VLS_93;
    let __VLS_94;
    const __VLS_95 = {
        onClick: (__VLS_ctx.applyWeights)
    };
    var __VLS_91;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "weight-row" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    const __VLS_96 = {}.Slider;
    /** @type {[typeof __VLS_components.Slider, ]} */ ;
    // @ts-ignore
    const __VLS_97 = __VLS_asFunctionalComponent(__VLS_96, new __VLS_96({
        modelValue: (__VLS_ctx.strategyState.expansion_bias),
        min: (0),
        max: (1),
        step: (0.01),
    }));
    const __VLS_98 = __VLS_97({
        modelValue: (__VLS_ctx.strategyState.expansion_bias),
        min: (0),
        max: (1),
        step: (0.01),
    }, ...__VLS_functionalComponentArgsRest(__VLS_97));
    const __VLS_100 = {}.InputNumber;
    /** @type {[typeof __VLS_components.InputNumber, ]} */ ;
    // @ts-ignore
    const __VLS_101 = __VLS_asFunctionalComponent(__VLS_100, new __VLS_100({
        modelValue: (__VLS_ctx.strategyState.expansion_bias),
        min: (0),
        max: (1),
        step: (0.01),
        mode: "decimal",
        minFractionDigits: (2),
        maxFractionDigits: (2),
    }));
    const __VLS_102 = __VLS_101({
        modelValue: (__VLS_ctx.strategyState.expansion_bias),
        min: (0),
        max: (1),
        step: (0.01),
        mode: "decimal",
        minFractionDigits: (2),
        maxFractionDigits: (2),
    }, ...__VLS_functionalComponentArgsRest(__VLS_101));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "weight-row" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    const __VLS_104 = {}.Slider;
    /** @type {[typeof __VLS_components.Slider, ]} */ ;
    // @ts-ignore
    const __VLS_105 = __VLS_asFunctionalComponent(__VLS_104, new __VLS_104({
        modelValue: (__VLS_ctx.strategyState.support_bias),
        min: (0),
        max: (1),
        step: (0.01),
    }));
    const __VLS_106 = __VLS_105({
        modelValue: (__VLS_ctx.strategyState.support_bias),
        min: (0),
        max: (1),
        step: (0.01),
    }, ...__VLS_functionalComponentArgsRest(__VLS_105));
    const __VLS_108 = {}.InputNumber;
    /** @type {[typeof __VLS_components.InputNumber, ]} */ ;
    // @ts-ignore
    const __VLS_109 = __VLS_asFunctionalComponent(__VLS_108, new __VLS_108({
        modelValue: (__VLS_ctx.strategyState.support_bias),
        min: (0),
        max: (1),
        step: (0.01),
        mode: "decimal",
        minFractionDigits: (2),
        maxFractionDigits: (2),
    }));
    const __VLS_110 = __VLS_109({
        modelValue: (__VLS_ctx.strategyState.support_bias),
        min: (0),
        max: (1),
        step: (0.01),
        mode: "decimal",
        minFractionDigits: (2),
        maxFractionDigits: (2),
    }, ...__VLS_functionalComponentArgsRest(__VLS_109));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "weight-row" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    const __VLS_112 = {}.Slider;
    /** @type {[typeof __VLS_components.Slider, ]} */ ;
    // @ts-ignore
    const __VLS_113 = __VLS_asFunctionalComponent(__VLS_112, new __VLS_112({
        modelValue: (__VLS_ctx.strategyState.boosted_cell_bias),
        min: (0),
        max: (1),
        step: (0.01),
    }));
    const __VLS_114 = __VLS_113({
        modelValue: (__VLS_ctx.strategyState.boosted_cell_bias),
        min: (0),
        max: (1),
        step: (0.01),
    }, ...__VLS_functionalComponentArgsRest(__VLS_113));
    const __VLS_116 = {}.InputNumber;
    /** @type {[typeof __VLS_components.InputNumber, ]} */ ;
    // @ts-ignore
    const __VLS_117 = __VLS_asFunctionalComponent(__VLS_116, new __VLS_116({
        modelValue: (__VLS_ctx.strategyState.boosted_cell_bias),
        min: (0),
        max: (1),
        step: (0.01),
        mode: "decimal",
        minFractionDigits: (2),
        maxFractionDigits: (2),
    }));
    const __VLS_118 = __VLS_117({
        modelValue: (__VLS_ctx.strategyState.boosted_cell_bias),
        min: (0),
        max: (1),
        step: (0.01),
        mode: "decimal",
        minFractionDigits: (2),
        maxFractionDigits: (2),
    }, ...__VLS_functionalComponentArgsRest(__VLS_117));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "weight-row" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    const __VLS_120 = {}.Slider;
    /** @type {[typeof __VLS_components.Slider, ]} */ ;
    // @ts-ignore
    const __VLS_121 = __VLS_asFunctionalComponent(__VLS_120, new __VLS_120({
        modelValue: (__VLS_ctx.strategyState.safety_bias),
        min: (0),
        max: (1),
        step: (0.01),
    }));
    const __VLS_122 = __VLS_121({
        modelValue: (__VLS_ctx.strategyState.safety_bias),
        min: (0),
        max: (1),
        step: (0.01),
    }, ...__VLS_functionalComponentArgsRest(__VLS_121));
    const __VLS_124 = {}.InputNumber;
    /** @type {[typeof __VLS_components.InputNumber, ]} */ ;
    // @ts-ignore
    const __VLS_125 = __VLS_asFunctionalComponent(__VLS_124, new __VLS_124({
        modelValue: (__VLS_ctx.strategyState.safety_bias),
        min: (0),
        max: (1),
        step: (0.01),
        mode: "decimal",
        minFractionDigits: (2),
        maxFractionDigits: (2),
    }));
    const __VLS_126 = __VLS_125({
        modelValue: (__VLS_ctx.strategyState.safety_bias),
        min: (0),
        max: (1),
        step: (0.01),
        mode: "decimal",
        minFractionDigits: (2),
        maxFractionDigits: (2),
    }, ...__VLS_functionalComponentArgsRest(__VLS_125));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "weight-row" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    const __VLS_128 = {}.Slider;
    /** @type {[typeof __VLS_components.Slider, ]} */ ;
    // @ts-ignore
    const __VLS_129 = __VLS_asFunctionalComponent(__VLS_128, new __VLS_128({
        modelValue: (__VLS_ctx.strategyState.beaver_hunt_bias),
        min: (0),
        max: (1),
        step: (0.01),
    }));
    const __VLS_130 = __VLS_129({
        modelValue: (__VLS_ctx.strategyState.beaver_hunt_bias),
        min: (0),
        max: (1),
        step: (0.01),
    }, ...__VLS_functionalComponentArgsRest(__VLS_129));
    const __VLS_132 = {}.InputNumber;
    /** @type {[typeof __VLS_components.InputNumber, ]} */ ;
    // @ts-ignore
    const __VLS_133 = __VLS_asFunctionalComponent(__VLS_132, new __VLS_132({
        modelValue: (__VLS_ctx.strategyState.beaver_hunt_bias),
        min: (0),
        max: (1),
        step: (0.01),
        mode: "decimal",
        minFractionDigits: (2),
        maxFractionDigits: (2),
    }));
    const __VLS_134 = __VLS_133({
        modelValue: (__VLS_ctx.strategyState.beaver_hunt_bias),
        min: (0),
        max: (1),
        step: (0.01),
        mode: "decimal",
        minFractionDigits: (2),
        maxFractionDigits: (2),
    }, ...__VLS_functionalComponentArgsRest(__VLS_133));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "weight-row" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    const __VLS_136 = {}.Slider;
    /** @type {[typeof __VLS_components.Slider, ]} */ ;
    // @ts-ignore
    const __VLS_137 = __VLS_asFunctionalComponent(__VLS_136, new __VLS_136({
        modelValue: (__VLS_ctx.strategyState.sabotage_bias),
        min: (0),
        max: (1),
        step: (0.01),
    }));
    const __VLS_138 = __VLS_137({
        modelValue: (__VLS_ctx.strategyState.sabotage_bias),
        min: (0),
        max: (1),
        step: (0.01),
    }, ...__VLS_functionalComponentArgsRest(__VLS_137));
    const __VLS_140 = {}.InputNumber;
    /** @type {[typeof __VLS_components.InputNumber, ]} */ ;
    // @ts-ignore
    const __VLS_141 = __VLS_asFunctionalComponent(__VLS_140, new __VLS_140({
        modelValue: (__VLS_ctx.strategyState.sabotage_bias),
        min: (0),
        max: (1),
        step: (0.01),
        mode: "decimal",
        minFractionDigits: (2),
        maxFractionDigits: (2),
    }));
    const __VLS_142 = __VLS_141({
        modelValue: (__VLS_ctx.strategyState.sabotage_bias),
        min: (0),
        max: (1),
        step: (0.01),
        mode: "decimal",
        minFractionDigits: (2),
        maxFractionDigits: (2),
    }, ...__VLS_functionalComponentArgsRest(__VLS_141));
    const __VLS_144 = {}.Divider;
    /** @type {[typeof __VLS_components.Divider, ]} */ ;
    // @ts-ignore
    const __VLS_145 = __VLS_asFunctionalComponent(__VLS_144, new __VLS_144({}));
    const __VLS_146 = __VLS_145({}, ...__VLS_functionalComponentArgsRest(__VLS_145));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "stacked-section" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "section-header" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({
        ...{ class: "section-label" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
        ...{ class: "section-subtitle" },
    });
    const __VLS_148 = {}.ToggleButton;
    /** @type {[typeof __VLS_components.ToggleButton, ]} */ ;
    // @ts-ignore
    const __VLS_149 = __VLS_asFunctionalComponent(__VLS_148, new __VLS_148({
        modelValue: (__VLS_ctx.commandModeModel),
        onLabel: "Command",
        offLabel: "Browse",
        onIcon: "pi pi-crosshairs",
        offIcon: "pi pi-eye",
    }));
    const __VLS_150 = __VLS_149({
        modelValue: (__VLS_ctx.commandModeModel),
        onLabel: "Command",
        offLabel: "Browse",
        onIcon: "pi pi-crosshairs",
        offIcon: "pi pi-eye",
    }, ...__VLS_functionalComponentArgsRest(__VLS_149));
    const __VLS_152 = {}.SelectButton;
    /** @type {[typeof __VLS_components.SelectButton, ]} */ ;
    // @ts-ignore
    const __VLS_153 = __VLS_asFunctionalComponent(__VLS_152, new __VLS_152({
        modelValue: (__VLS_ctx.manualActionModel),
        options: (__VLS_ctx.manualActionOptions),
        optionLabel: "label",
        optionValue: "value",
    }));
    const __VLS_154 = __VLS_153({
        modelValue: (__VLS_ctx.manualActionModel),
        options: (__VLS_ctx.manualActionOptions),
        optionLabel: "label",
        optionValue: "value",
    }, ...__VLS_functionalComponentArgsRest(__VLS_153));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
        ...{ class: "hint-text" },
    });
    (__VLS_ctx.commandHint);
    const __VLS_156 = {}.Divider;
    /** @type {[typeof __VLS_components.Divider, ]} */ ;
    // @ts-ignore
    const __VLS_157 = __VLS_asFunctionalComponent(__VLS_156, new __VLS_156({}));
    const __VLS_158 = __VLS_157({}, ...__VLS_functionalComponentArgsRest(__VLS_157));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "stacked-section" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "section-header" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.label, __VLS_intrinsicElements.label)({
        ...{ class: "section-label" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
        ...{ class: "section-subtitle" },
    });
    (__VLS_ctx.world?.recommended_upgrade?.reason ?? 'Пока автоматическая рекомендация не сформирована.');
    if (__VLS_ctx.world?.recommended_upgrade) {
        const __VLS_160 = {}.Tag;
        /** @type {[typeof __VLS_components.Tag, ]} */ ;
        // @ts-ignore
        const __VLS_161 = __VLS_asFunctionalComponent(__VLS_160, new __VLS_160({
            severity: "info",
            value: (`auto: ${__VLS_ctx.world.recommended_upgrade.name}`),
        }));
        const __VLS_162 = __VLS_161({
            severity: "info",
            value: (`auto: ${__VLS_ctx.world.recommended_upgrade.name}`),
        }, ...__VLS_functionalComponentArgsRest(__VLS_161));
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "form-row" },
    });
    const __VLS_164 = {}.Select;
    /** @type {[typeof __VLS_components.Select, ]} */ ;
    // @ts-ignore
    const __VLS_165 = __VLS_asFunctionalComponent(__VLS_164, new __VLS_164({
        modelValue: (__VLS_ctx.forcedUpgrade),
        options: (__VLS_ctx.upgradeOptions),
        optionLabel: "label",
        optionValue: "value",
        placeholder: "Выбрать апгрейд",
    }));
    const __VLS_166 = __VLS_165({
        modelValue: (__VLS_ctx.forcedUpgrade),
        options: (__VLS_ctx.upgradeOptions),
        optionLabel: "label",
        optionValue: "value",
        placeholder: "Выбрать апгрейд",
    }, ...__VLS_functionalComponentArgsRest(__VLS_165));
    const __VLS_168 = {}.Button;
    /** @type {[typeof __VLS_components.Button, ]} */ ;
    // @ts-ignore
    const __VLS_169 = __VLS_asFunctionalComponent(__VLS_168, new __VLS_168({
        ...{ 'onClick': {} },
        label: "Поставить в очередь",
        icon: "pi pi-plus",
        severity: "secondary",
    }));
    const __VLS_170 = __VLS_169({
        ...{ 'onClick': {} },
        label: "Поставить в очередь",
        icon: "pi pi-plus",
        severity: "secondary",
    }, ...__VLS_functionalComponentArgsRest(__VLS_169));
    let __VLS_172;
    let __VLS_173;
    let __VLS_174;
    const __VLS_175 = {
        onClick: (__VLS_ctx.forceUpgrade)
    };
    var __VLS_171;
}
var __VLS_3;
/** @type {__VLS_StyleScopedClasses['control-panel']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-card']} */ ;
/** @type {__VLS_StyleScopedClasses['control-panel-card']} */ ;
/** @type {__VLS_StyleScopedClasses['panel-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['button-row']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-item']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-item']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-item']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-item']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
/** @type {__VLS_StyleScopedClasses['stacked-section']} */ ;
/** @type {__VLS_StyleScopedClasses['section-header']} */ ;
/** @type {__VLS_StyleScopedClasses['section-label']} */ ;
/** @type {__VLS_StyleScopedClasses['section-subtitle']} */ ;
/** @type {__VLS_StyleScopedClasses['form-row']} */ ;
/** @type {__VLS_StyleScopedClasses['form-row']} */ ;
/** @type {__VLS_StyleScopedClasses['stacked-section']} */ ;
/** @type {__VLS_StyleScopedClasses['section-label']} */ ;
/** @type {__VLS_StyleScopedClasses['stacked-section']} */ ;
/** @type {__VLS_StyleScopedClasses['section-header']} */ ;
/** @type {__VLS_StyleScopedClasses['section-label']} */ ;
/** @type {__VLS_StyleScopedClasses['section-subtitle']} */ ;
/** @type {__VLS_StyleScopedClasses['weight-row']} */ ;
/** @type {__VLS_StyleScopedClasses['weight-row']} */ ;
/** @type {__VLS_StyleScopedClasses['weight-row']} */ ;
/** @type {__VLS_StyleScopedClasses['weight-row']} */ ;
/** @type {__VLS_StyleScopedClasses['weight-row']} */ ;
/** @type {__VLS_StyleScopedClasses['weight-row']} */ ;
/** @type {__VLS_StyleScopedClasses['stacked-section']} */ ;
/** @type {__VLS_StyleScopedClasses['section-header']} */ ;
/** @type {__VLS_StyleScopedClasses['section-label']} */ ;
/** @type {__VLS_StyleScopedClasses['section-subtitle']} */ ;
/** @type {__VLS_StyleScopedClasses['hint-text']} */ ;
/** @type {__VLS_StyleScopedClasses['stacked-section']} */ ;
/** @type {__VLS_StyleScopedClasses['section-header']} */ ;
/** @type {__VLS_StyleScopedClasses['section-label']} */ ;
/** @type {__VLS_StyleScopedClasses['section-subtitle']} */ ;
/** @type {__VLS_StyleScopedClasses['form-row']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            Button: Button,
            Card: Card,
            Divider: Divider,
            InputNumber: InputNumber,
            Select: Select,
            SelectButton: SelectButton,
            Slider: Slider,
            Tag: Tag,
            ToggleButton: ToggleButton,
            store: store,
            strategyState: strategyState,
            providerKey: providerKey,
            submitMode: submitMode,
            forcedUpgrade: forcedUpgrade,
            commandModeModel: commandModeModel,
            manualActionModel: manualActionModel,
            strategyOptions: strategyOptions,
            providerOptions: providerOptions,
            submitModeOptions: submitModeOptions,
            manualActionOptions: manualActionOptions,
            upgradeOptions: upgradeOptions,
            commandHint: commandHint,
            applyStrategy: applyStrategy,
            applyWeights: applyWeights,
            applyProvider: applyProvider,
            applySubmitMode: applySubmitMode,
            forceUpgrade: forceUpgrade,
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
