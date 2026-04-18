import { ref } from 'vue';
import Card from 'primevue/card';
import Drawer from 'primevue/drawer';
import Button from 'primevue/button';
import Tag from 'primevue/tag';
import ControlPanel from '@/components/control/ControlPanel.vue';
import InspectorCard from '@/components/dashboard/InspectorCard.vue';
import PlanBoard from '@/components/dashboard/PlanBoard.vue';
import GameCanvas from '@/components/map/GameCanvas.vue';
import { useCommandCenterStore } from '@/stores/commandCenter';
const store = useCommandCenterStore();
const commandMode = ref(false);
const manualActionKind = ref('build');
const selectedPlantationIds = ref([]);
const controlDrawerOpen = ref(false);
const canvasRef = ref(null);
const inspected = ref(null);
function focusMainPlantation() {
    canvasRef.value?.focusMainPlantation();
}
async function onCommandTarget(payload) {
    if (!commandMode.value || !store.world)
        return;
    if (manualActionKind.value === 'build') {
        await store.createDirective({
            kind: 'build',
            author_ids: selectedPlantationIds.value,
            target_position: payload.position,
            ttl_turns: 4,
            note: `manual build ${payload.position.x},${payload.position.y}`,
        });
        return;
    }
    if (manualActionKind.value === 'repair' && payload.entityKind === 'plantation' && payload.own && payload.entityId) {
        await store.createDirective({
            kind: 'repair',
            author_ids: selectedPlantationIds.value,
            target_position: payload.position,
            target_entity_id: payload.entityId,
            ttl_turns: 2,
            note: `manual repair ${payload.entityId}`,
        });
        return;
    }
    if (manualActionKind.value === 'sabotage' && payload.entityKind === 'enemy' && payload.entityId) {
        await store.createDirective({
            kind: 'sabotage',
            author_ids: selectedPlantationIds.value,
            target_position: payload.position,
            target_entity_id: payload.entityId,
            ttl_turns: 2,
            note: `manual sabotage ${payload.entityId}`,
        });
        return;
    }
    if (manualActionKind.value === 'beaver_attack' && payload.entityKind === 'beaver' && payload.entityId) {
        await store.createDirective({
            kind: 'beaver_attack',
            author_ids: selectedPlantationIds.value,
            target_position: payload.position,
            target_entity_id: payload.entityId,
            ttl_turns: 2,
            note: `manual beaver focus ${payload.entityId}`,
        });
        return;
    }
    if (manualActionKind.value === 'relocate_main' && payload.entityKind === 'plantation' && payload.own && payload.entityId) {
        await store.createDirective({
            kind: 'relocate_main',
            relocate_to_id: payload.entityId,
            ttl_turns: 2,
            note: `manual relocate main ${payload.entityId}`,
        });
    }
}
function readinessSeverity(connected, isolated) {
    if (connected === 0)
        return 'danger';
    if (isolated > 0)
        return 'warn';
    return 'success';
}
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.section, __VLS_intrinsicElements.section)({
    ...{ class: "view-grid" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "visualization-toolbar" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "visualization-toolbar__meta" },
});
const __VLS_0 = {}.Tag;
/** @type {[typeof __VLS_components.Tag, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    severity: "info",
    value: (`Ход ${__VLS_ctx.store.world?.turn ?? 0}`),
}));
const __VLS_2 = __VLS_1({
    severity: "info",
    value: (`Ход ${__VLS_ctx.store.world?.turn ?? 0}`),
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
const __VLS_4 = {}.Tag;
/** @type {[typeof __VLS_components.Tag, ]} */ ;
// @ts-ignore
const __VLS_5 = __VLS_asFunctionalComponent(__VLS_4, new __VLS_4({
    severity: "success",
    value: (`Сеть ${__VLS_ctx.store.world?.stats.connected_plantations ?? 0}`),
}));
const __VLS_6 = __VLS_5({
    severity: "success",
    value: (`Сеть ${__VLS_ctx.store.world?.stats.connected_plantations ?? 0}`),
}, ...__VLS_functionalComponentArgsRest(__VLS_5));
const __VLS_8 = {}.Tag;
/** @type {[typeof __VLS_components.Tag, ]} */ ;
// @ts-ignore
const __VLS_9 = __VLS_asFunctionalComponent(__VLS_8, new __VLS_8({
    severity: "warn",
    value: (`Бобры ${__VLS_ctx.store.world?.stats.visible_beavers ?? 0}`),
}));
const __VLS_10 = __VLS_9({
    severity: "warn",
    value: (`Бобры ${__VLS_ctx.store.world?.stats.visible_beavers ?? 0}`),
}, ...__VLS_functionalComponentArgsRest(__VLS_9));
const __VLS_12 = {}.Tag;
/** @type {[typeof __VLS_components.Tag, ]} */ ;
// @ts-ignore
const __VLS_13 = __VLS_asFunctionalComponent(__VLS_12, new __VLS_12({
    severity: "secondary",
    value: (`Выделено ${__VLS_ctx.selectedPlantationIds.length}`),
}));
const __VLS_14 = __VLS_13({
    severity: "secondary",
    value: (`Выделено ${__VLS_ctx.selectedPlantationIds.length}`),
}, ...__VLS_functionalComponentArgsRest(__VLS_13));
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "visualization-toolbar__actions" },
});
const __VLS_16 = {}.Button;
/** @type {[typeof __VLS_components.Button, ]} */ ;
// @ts-ignore
const __VLS_17 = __VLS_asFunctionalComponent(__VLS_16, new __VLS_16({
    ...{ 'onClick': {} },
    icon: "pi pi-crosshairs",
    label: "Найти ЦУ",
    severity: "secondary",
    outlined: true,
}));
const __VLS_18 = __VLS_17({
    ...{ 'onClick': {} },
    icon: "pi pi-crosshairs",
    label: "Найти ЦУ",
    severity: "secondary",
    outlined: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_17));
let __VLS_20;
let __VLS_21;
let __VLS_22;
const __VLS_23 = {
    onClick: (__VLS_ctx.focusMainPlantation)
};
var __VLS_19;
const __VLS_24 = {}.Button;
/** @type {[typeof __VLS_components.Button, ]} */ ;
// @ts-ignore
const __VLS_25 = __VLS_asFunctionalComponent(__VLS_24, new __VLS_24({
    ...{ 'onClick': {} },
    icon: "pi pi-sliders-h",
    label: "Панель управления",
    ...{ class: "drawer-toggle-button" },
}));
const __VLS_26 = __VLS_25({
    ...{ 'onClick': {} },
    icon: "pi pi-sliders-h",
    label: "Панель управления",
    ...{ class: "drawer-toggle-button" },
}, ...__VLS_functionalComponentArgsRest(__VLS_25));
let __VLS_28;
let __VLS_29;
let __VLS_30;
const __VLS_31 = {
    onClick: (...[$event]) => {
        __VLS_ctx.controlDrawerOpen = true;
    }
};
var __VLS_27;
const __VLS_32 = {}.Card;
/** @type {[typeof __VLS_components.Card, typeof __VLS_components.Card, ]} */ ;
// @ts-ignore
const __VLS_33 = __VLS_asFunctionalComponent(__VLS_32, new __VLS_32({
    ...{ class: "canvas-card canvas-card--wide" },
}));
const __VLS_34 = __VLS_33({
    ...{ class: "canvas-card canvas-card--wide" },
}, ...__VLS_functionalComponentArgsRest(__VLS_33));
__VLS_35.slots.default;
{
    const { content: __VLS_thisSlot } = __VLS_35.slots;
    /** @type {[typeof GameCanvas, ]} */ ;
    // @ts-ignore
    const __VLS_36 = __VLS_asFunctionalComponent(GameCanvas, new GameCanvas({
        ...{ 'onSelectionChange': {} },
        ...{ 'onCommandTarget': {} },
        ...{ 'onInspectChange': {} },
        ref: "canvasRef",
        world: (__VLS_ctx.store.world),
        commandMode: (__VLS_ctx.commandMode),
        manualActionKind: (__VLS_ctx.manualActionKind),
        selectedPlantationIds: (__VLS_ctx.selectedPlantationIds),
    }));
    const __VLS_37 = __VLS_36({
        ...{ 'onSelectionChange': {} },
        ...{ 'onCommandTarget': {} },
        ...{ 'onInspectChange': {} },
        ref: "canvasRef",
        world: (__VLS_ctx.store.world),
        commandMode: (__VLS_ctx.commandMode),
        manualActionKind: (__VLS_ctx.manualActionKind),
        selectedPlantationIds: (__VLS_ctx.selectedPlantationIds),
    }, ...__VLS_functionalComponentArgsRest(__VLS_36));
    let __VLS_39;
    let __VLS_40;
    let __VLS_41;
    const __VLS_42 = {
        onSelectionChange: (...[$event]) => {
            __VLS_ctx.selectedPlantationIds = $event;
        }
    };
    const __VLS_43 = {
        onCommandTarget: (__VLS_ctx.onCommandTarget)
    };
    const __VLS_44 = {
        onInspectChange: (...[$event]) => {
            __VLS_ctx.inspected = $event;
        }
    };
    /** @type {typeof __VLS_ctx.canvasRef} */ ;
    var __VLS_45 = {};
    var __VLS_38;
}
var __VLS_35;
const __VLS_47 = {}.Drawer;
/** @type {[typeof __VLS_components.Drawer, typeof __VLS_components.Drawer, ]} */ ;
// @ts-ignore
const __VLS_48 = __VLS_asFunctionalComponent(__VLS_47, new __VLS_47({
    visible: (__VLS_ctx.controlDrawerOpen),
    position: "right",
    ...{ class: "control-drawer" },
}));
const __VLS_49 = __VLS_48({
    visible: (__VLS_ctx.controlDrawerOpen),
    position: "right",
    ...{ class: "control-drawer" },
}, ...__VLS_functionalComponentArgsRest(__VLS_48));
__VLS_50.slots.default;
{
    const { header: __VLS_thisSlot } = __VLS_50.slots;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "drawer-header" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "drawer-header__copy" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "drawer-eyebrow" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    const __VLS_51 = {}.Tag;
    /** @type {[typeof __VLS_components.Tag, ]} */ ;
    // @ts-ignore
    const __VLS_52 = __VLS_asFunctionalComponent(__VLS_51, new __VLS_51({
        severity: (__VLS_ctx.store.runtime?.status === 'running' ? 'success' : __VLS_ctx.store.runtime?.status === 'error' ? 'danger' : 'warn'),
        value: (__VLS_ctx.store.runtime?.status ?? 'booting'),
    }));
    const __VLS_53 = __VLS_52({
        severity: (__VLS_ctx.store.runtime?.status === 'running' ? 'success' : __VLS_ctx.store.runtime?.status === 'error' ? 'danger' : 'warn'),
        value: (__VLS_ctx.store.runtime?.status ?? 'booting'),
    }, ...__VLS_functionalComponentArgsRest(__VLS_52));
}
/** @type {[typeof ControlPanel, ]} */ ;
// @ts-ignore
const __VLS_55 = __VLS_asFunctionalComponent(ControlPanel, new ControlPanel({
    ...{ 'onUpdate:commandMode': {} },
    ...{ 'onUpdate:manualActionKind': {} },
    runtime: (__VLS_ctx.store.runtime),
    world: (__VLS_ctx.store.world),
    selectedPlantationIds: (__VLS_ctx.selectedPlantationIds),
    commandMode: (__VLS_ctx.commandMode),
    manualActionKind: (__VLS_ctx.manualActionKind),
}));
const __VLS_56 = __VLS_55({
    ...{ 'onUpdate:commandMode': {} },
    ...{ 'onUpdate:manualActionKind': {} },
    runtime: (__VLS_ctx.store.runtime),
    world: (__VLS_ctx.store.world),
    selectedPlantationIds: (__VLS_ctx.selectedPlantationIds),
    commandMode: (__VLS_ctx.commandMode),
    manualActionKind: (__VLS_ctx.manualActionKind),
}, ...__VLS_functionalComponentArgsRest(__VLS_55));
let __VLS_58;
let __VLS_59;
let __VLS_60;
const __VLS_61 = {
    'onUpdate:commandMode': (...[$event]) => {
        __VLS_ctx.commandMode = $event;
    }
};
const __VLS_62 = {
    'onUpdate:manualActionKind': (...[$event]) => {
        __VLS_ctx.manualActionKind = $event;
    }
};
var __VLS_57;
var __VLS_50;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "summary-grid" },
});
const __VLS_63 = {}.Card;
/** @type {[typeof __VLS_components.Card, typeof __VLS_components.Card, ]} */ ;
// @ts-ignore
const __VLS_64 = __VLS_asFunctionalComponent(__VLS_63, new __VLS_63({
    ...{ class: "summary-card" },
}));
const __VLS_65 = __VLS_64({
    ...{ class: "summary-card" },
}, ...__VLS_functionalComponentArgsRest(__VLS_64));
__VLS_66.slots.default;
{
    const { title: __VLS_thisSlot } = __VLS_66.slots;
}
{
    const { content: __VLS_thisSlot } = __VLS_66.slots;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "summary-lines" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "summary-line" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    (__VLS_ctx.store.world?.turn ?? 0);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "summary-line" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    (__VLS_ctx.store.world?.next_turn_in?.toFixed(2) ?? '0.00');
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "summary-line" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    (__VLS_ctx.store.runtime?.active_strategy_key ?? 'frontier');
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "summary-line" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    (__VLS_ctx.store.runtime?.submit_mode ?? 'mock');
}
var __VLS_66;
const __VLS_67 = {}.Card;
/** @type {[typeof __VLS_components.Card, typeof __VLS_components.Card, ]} */ ;
// @ts-ignore
const __VLS_68 = __VLS_asFunctionalComponent(__VLS_67, new __VLS_67({
    ...{ class: "summary-card" },
}));
const __VLS_69 = __VLS_68({
    ...{ class: "summary-card" },
}, ...__VLS_functionalComponentArgsRest(__VLS_68));
__VLS_70.slots.default;
{
    const { title: __VLS_thisSlot } = __VLS_70.slots;
}
{
    const { content: __VLS_thisSlot } = __VLS_70.slots;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "force-badges" },
    });
    const __VLS_71 = {}.Tag;
    /** @type {[typeof __VLS_components.Tag, ]} */ ;
    // @ts-ignore
    const __VLS_72 = __VLS_asFunctionalComponent(__VLS_71, new __VLS_71({
        severity: "info",
        value: (`Доход ${__VLS_ctx.store.world?.stats.current_income_per_tick ?? 0}/ход`),
    }));
    const __VLS_73 = __VLS_72({
        severity: "info",
        value: (`Доход ${__VLS_ctx.store.world?.stats.current_income_per_tick ?? 0}/ход`),
    }, ...__VLS_functionalComponentArgsRest(__VLS_72));
    const __VLS_75 = {}.Tag;
    /** @type {[typeof __VLS_components.Tag, ]} */ ;
    // @ts-ignore
    const __VLS_76 = __VLS_asFunctionalComponent(__VLS_75, new __VLS_75({
        severity: "success",
        value: (`Сеть ${__VLS_ctx.store.world?.stats.connected_plantations ?? 0}`),
    }));
    const __VLS_77 = __VLS_76({
        severity: "success",
        value: (`Сеть ${__VLS_ctx.store.world?.stats.connected_plantations ?? 0}`),
    }, ...__VLS_functionalComponentArgsRest(__VLS_76));
    const __VLS_79 = {}.Tag;
    /** @type {[typeof __VLS_components.Tag, ]} */ ;
    // @ts-ignore
    const __VLS_80 = __VLS_asFunctionalComponent(__VLS_79, new __VLS_79({
        severity: "warn",
        value: (`Изолировано ${__VLS_ctx.store.world?.stats.isolated_plantations ?? 0}`),
    }));
    const __VLS_81 = __VLS_80({
        severity: "warn",
        value: (`Изолировано ${__VLS_ctx.store.world?.stats.isolated_plantations ?? 0}`),
    }, ...__VLS_functionalComponentArgsRest(__VLS_80));
    const __VLS_83 = {}.Tag;
    /** @type {[typeof __VLS_components.Tag, ]} */ ;
    // @ts-ignore
    const __VLS_84 = __VLS_asFunctionalComponent(__VLS_83, new __VLS_83({
        severity: "secondary",
        value: (`Лимит ${__VLS_ctx.store.world?.stats.available_settlement_headroom ?? 0}`),
    }));
    const __VLS_85 = __VLS_84({
        severity: "secondary",
        value: (`Лимит ${__VLS_ctx.store.world?.stats.available_settlement_headroom ?? 0}`),
    }, ...__VLS_functionalComponentArgsRest(__VLS_84));
    const __VLS_87 = {}.Tag;
    /** @type {[typeof __VLS_components.Tag, ]} */ ;
    // @ts-ignore
    const __VLS_88 = __VLS_asFunctionalComponent(__VLS_87, new __VLS_87({
        severity: "contrast",
        value: (`Бобры ${__VLS_ctx.store.world?.stats.visible_beavers ?? 0}`),
    }));
    const __VLS_89 = __VLS_88({
        severity: "contrast",
        value: (`Бобры ${__VLS_ctx.store.world?.stats.visible_beavers ?? 0}`),
    }, ...__VLS_functionalComponentArgsRest(__VLS_88));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "summary-lines top-gap" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "summary-line" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    const __VLS_91 = {}.Tag;
    /** @type {[typeof __VLS_components.Tag, ]} */ ;
    // @ts-ignore
    const __VLS_92 = __VLS_asFunctionalComponent(__VLS_91, new __VLS_91({
        severity: (__VLS_ctx.readinessSeverity(__VLS_ctx.store.world?.stats.connected_plantations ?? 0, __VLS_ctx.store.world?.stats.isolated_plantations ?? 0)),
        value: ((__VLS_ctx.store.world?.stats.isolated_plantations ?? 0) > 0 ? 'нужен ремонт сети' : 'стабильна'),
    }));
    const __VLS_93 = __VLS_92({
        severity: (__VLS_ctx.readinessSeverity(__VLS_ctx.store.world?.stats.connected_plantations ?? 0, __VLS_ctx.store.world?.stats.isolated_plantations ?? 0)),
        value: ((__VLS_ctx.store.world?.stats.isolated_plantations ?? 0) > 0 ? 'нужен ремонт сети' : 'стабильна'),
    }, ...__VLS_functionalComponentArgsRest(__VLS_92));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "summary-line" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    (__VLS_ctx.store.world?.upgrades.points ?? 0);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "summary-line" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    (__VLS_ctx.selectedPlantationIds.length);
}
var __VLS_70;
/** @type {[typeof InspectorCard, ]} */ ;
// @ts-ignore
const __VLS_95 = __VLS_asFunctionalComponent(InspectorCard, new InspectorCard({
    world: (__VLS_ctx.store.world),
    inspected: (__VLS_ctx.inspected),
}));
const __VLS_96 = __VLS_95({
    world: (__VLS_ctx.store.world),
    inspected: (__VLS_ctx.inspected),
}, ...__VLS_functionalComponentArgsRest(__VLS_95));
/** @type {[typeof PlanBoard, ]} */ ;
// @ts-ignore
const __VLS_98 = __VLS_asFunctionalComponent(PlanBoard, new PlanBoard({
    world: (__VLS_ctx.store.world),
}));
const __VLS_99 = __VLS_98({
    world: (__VLS_ctx.store.world),
}, ...__VLS_functionalComponentArgsRest(__VLS_98));
/** @type {__VLS_StyleScopedClasses['view-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['visualization-toolbar']} */ ;
/** @type {__VLS_StyleScopedClasses['visualization-toolbar__meta']} */ ;
/** @type {__VLS_StyleScopedClasses['visualization-toolbar__actions']} */ ;
/** @type {__VLS_StyleScopedClasses['drawer-toggle-button']} */ ;
/** @type {__VLS_StyleScopedClasses['canvas-card']} */ ;
/** @type {__VLS_StyleScopedClasses['canvas-card--wide']} */ ;
/** @type {__VLS_StyleScopedClasses['control-drawer']} */ ;
/** @type {__VLS_StyleScopedClasses['drawer-header']} */ ;
/** @type {__VLS_StyleScopedClasses['drawer-header__copy']} */ ;
/** @type {__VLS_StyleScopedClasses['drawer-eyebrow']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-card']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-lines']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-card']} */ ;
/** @type {__VLS_StyleScopedClasses['force-badges']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-lines']} */ ;
/** @type {__VLS_StyleScopedClasses['top-gap']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
// @ts-ignore
var __VLS_46 = __VLS_45;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            Card: Card,
            Drawer: Drawer,
            Button: Button,
            Tag: Tag,
            ControlPanel: ControlPanel,
            InspectorCard: InspectorCard,
            PlanBoard: PlanBoard,
            GameCanvas: GameCanvas,
            store: store,
            commandMode: commandMode,
            manualActionKind: manualActionKind,
            selectedPlantationIds: selectedPlantationIds,
            controlDrawerOpen: controlDrawerOpen,
            canvasRef: canvasRef,
            inspected: inspected,
            focusMainPlantation: focusMainPlantation,
            onCommandTarget: onCommandTarget,
            readinessSeverity: readinessSeverity,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
