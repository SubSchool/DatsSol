import { computed } from 'vue';
import Card from 'primevue/card';
import Tag from 'primevue/tag';
const props = defineProps();
const plantation = computed(() => props.inspected?.entityKind === 'plantation'
    ? props.world?.plantations.find((item) => item.id === props.inspected?.entityId)
    : null);
const enemy = computed(() => props.inspected?.entityKind === 'enemy'
    ? props.world?.enemy.find((item) => item.id === props.inspected?.entityId)
    : null);
const beaver = computed(() => props.inspected?.entityKind === 'beaver'
    ? props.world?.beavers.find((item) => item.id === props.inspected?.entityId)
    : null);
const construction = computed(() => props.inspected?.entityKind === 'construction'
    ? props.world?.constructions.find((item) => item.position.x === props.inspected?.position.x &&
        item.position.y === props.inspected?.position.y)
    : null);
const cell = computed(() => props.world?.cells.find((item) => item.position.x === props.inspected?.position.x &&
    item.position.y === props.inspected?.position.y) ?? null);
function yesNoSeverity(value) {
    return value ? 'success' : 'secondary';
}
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
const __VLS_0 = {}.Card;
/** @type {[typeof __VLS_components.Card, typeof __VLS_components.Card, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    ...{ class: "summary-card inspector-card" },
}));
const __VLS_2 = __VLS_1({
    ...{ class: "summary-card inspector-card" },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
var __VLS_4 = {};
__VLS_3.slots.default;
{
    const { title: __VLS_thisSlot } = __VLS_3.slots;
}
{
    const { content: __VLS_thisSlot } = __VLS_3.slots;
    if (__VLS_ctx.inspected) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "inspector-stack" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "summary-line" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
        (__VLS_ctx.inspected.position.x);
        (__VLS_ctx.inspected.position.y);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "summary-line" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        const __VLS_5 = {}.Tag;
        /** @type {[typeof __VLS_components.Tag, ]} */ ;
        // @ts-ignore
        const __VLS_6 = __VLS_asFunctionalComponent(__VLS_5, new __VLS_5({
            severity: (__VLS_ctx.yesNoSeverity(__VLS_ctx.inspected.position.x % 7 === 0 && __VLS_ctx.inspected.position.y % 7 === 0)),
            value: (__VLS_ctx.inspected.position.x % 7 === 0 && __VLS_ctx.inspected.position.y % 7 === 0 ? 'да' : 'нет'),
        }));
        const __VLS_7 = __VLS_6({
            severity: (__VLS_ctx.yesNoSeverity(__VLS_ctx.inspected.position.x % 7 === 0 && __VLS_ctx.inspected.position.y % 7 === 0)),
            value: (__VLS_ctx.inspected.position.x % 7 === 0 && __VLS_ctx.inspected.position.y % 7 === 0 ? 'да' : 'нет'),
        }, ...__VLS_functionalComponentArgsRest(__VLS_6));
        if (__VLS_ctx.plantation) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "summary-line" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (__VLS_ctx.plantation.id);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "summary-line" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (__VLS_ctx.plantation.hp);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "summary-line" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (__VLS_ctx.plantation.role);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "summary-line" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            const __VLS_9 = {}.Tag;
            /** @type {[typeof __VLS_components.Tag, ]} */ ;
            // @ts-ignore
            const __VLS_10 = __VLS_asFunctionalComponent(__VLS_9, new __VLS_9({
                severity: (__VLS_ctx.yesNoSeverity(__VLS_ctx.plantation.connected)),
                value: (__VLS_ctx.plantation.connected ? 'да' : 'нет'),
            }));
            const __VLS_11 = __VLS_10({
                severity: (__VLS_ctx.yesNoSeverity(__VLS_ctx.plantation.connected)),
                value: (__VLS_ctx.plantation.connected ? 'да' : 'нет'),
            }, ...__VLS_functionalComponentArgsRest(__VLS_10));
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "summary-line" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (__VLS_ctx.plantation.immunity_until_turn);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "summary-line" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (__VLS_ctx.plantation.terraform_progress);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "summary-line" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (__VLS_ctx.plantation.turns_to_completion ?? '-');
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "summary-line" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (__VLS_ctx.plantation.projected_income_per_turn);
        }
        else if (__VLS_ctx.enemy) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "summary-line" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (__VLS_ctx.enemy.id);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "summary-line" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (__VLS_ctx.enemy.hp);
        }
        else if (__VLS_ctx.beaver) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "summary-line" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (__VLS_ctx.beaver.id);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "summary-line" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (__VLS_ctx.beaver.hp);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "summary-line" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (__VLS_ctx.beaver.threat_score.toFixed(1));
        }
        else if (__VLS_ctx.construction) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "summary-line" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (__VLS_ctx.construction.progress);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "summary-line" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            const __VLS_13 = {}.Tag;
            /** @type {[typeof __VLS_components.Tag, ]} */ ;
            // @ts-ignore
            const __VLS_14 = __VLS_asFunctionalComponent(__VLS_13, new __VLS_13({
                severity: (__VLS_ctx.yesNoSeverity(__VLS_ctx.construction.is_boosted_cell)),
                value: (__VLS_ctx.construction.is_boosted_cell ? 'да' : 'нет'),
            }));
            const __VLS_15 = __VLS_14({
                severity: (__VLS_ctx.yesNoSeverity(__VLS_ctx.construction.is_boosted_cell)),
                value: (__VLS_ctx.construction.is_boosted_cell ? 'да' : 'нет'),
            }, ...__VLS_functionalComponentArgsRest(__VLS_14));
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "summary-line" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            const __VLS_17 = {}.Tag;
            /** @type {[typeof __VLS_components.Tag, ]} */ ;
            // @ts-ignore
            const __VLS_18 = __VLS_asFunctionalComponent(__VLS_17, new __VLS_17({
                severity: (__VLS_ctx.construction.threatened ? 'warn' : 'secondary'),
                value: (__VLS_ctx.construction.threatened ? 'да' : 'нет'),
            }));
            const __VLS_19 = __VLS_18({
                severity: (__VLS_ctx.construction.threatened ? 'warn' : 'secondary'),
                value: (__VLS_ctx.construction.threatened ? 'да' : 'нет'),
            }, ...__VLS_functionalComponentArgsRest(__VLS_18));
        }
        if (__VLS_ctx.cell) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "summary-line" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (__VLS_ctx.cell.terraformation_progress);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "summary-line" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (__VLS_ctx.cell.turns_until_degradation);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "summary-line" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (__VLS_ctx.cell.total_value);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "summary-line" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (__VLS_ctx.cell.income_per_tick);
        }
    }
    else {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
            ...{ class: "empty-state" },
        });
    }
}
var __VLS_3;
/** @type {__VLS_StyleScopedClasses['summary-card']} */ ;
/** @type {__VLS_StyleScopedClasses['inspector-card']} */ ;
/** @type {__VLS_StyleScopedClasses['inspector-stack']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            Card: Card,
            Tag: Tag,
            plantation: plantation,
            enemy: enemy,
            beaver: beaver,
            construction: construction,
            cell: cell,
            yesNoSeverity: yesNoSeverity,
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
