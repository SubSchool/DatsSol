import Card from 'primevue/card';
import Tag from 'primevue/tag';
const __VLS_props = defineProps();
function alertSeverity(level) {
    if (level === 'danger')
        return 'danger';
    if (level === 'warn')
        return 'warn';
    return 'info';
}
function pipelineSeverity(level) {
    if (level === 'error')
        return 'danger';
    if (level === 'warn')
        return 'warn';
    return 'success';
}
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "plan-board" },
});
const __VLS_0 = {}.Card;
/** @type {[typeof __VLS_components.Card, typeof __VLS_components.Card, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    ...{ class: "summary-card" },
}));
const __VLS_2 = __VLS_1({
    ...{ class: "summary-card" },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
__VLS_3.slots.default;
{
    const { title: __VLS_thisSlot } = __VLS_3.slots;
}
{
    const { content: __VLS_thisSlot } = __VLS_3.slots;
    if (__VLS_ctx.world?.alerts?.length) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "alert-list" },
        });
        for (const [alert] of __VLS_getVForSourceType((__VLS_ctx.world.alerts))) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                key: (alert.title),
                ...{ class: "alert-item" },
            });
            const __VLS_4 = {}.Tag;
            /** @type {[typeof __VLS_components.Tag, ]} */ ;
            // @ts-ignore
            const __VLS_5 = __VLS_asFunctionalComponent(__VLS_4, new __VLS_4({
                severity: (__VLS_ctx.alertSeverity(alert.severity)),
                value: (alert.title),
            }));
            const __VLS_6 = __VLS_5({
                severity: (__VLS_ctx.alertSeverity(alert.severity)),
                value: (alert.title),
            }, ...__VLS_functionalComponentArgsRest(__VLS_5));
            __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({});
            (alert.description);
        }
    }
    else {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
            ...{ class: "empty-state" },
        });
    }
    if (__VLS_ctx.world?.highlights?.length) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.ul, __VLS_intrinsicElements.ul)({
            ...{ class: "highlight-list top-gap" },
        });
        for (const [line] of __VLS_getVForSourceType((__VLS_ctx.world.highlights))) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.li, __VLS_intrinsicElements.li)({
                key: (line),
            });
            (line);
        }
    }
}
var __VLS_3;
const __VLS_8 = {}.Card;
/** @type {[typeof __VLS_components.Card, typeof __VLS_components.Card, ]} */ ;
// @ts-ignore
const __VLS_9 = __VLS_asFunctionalComponent(__VLS_8, new __VLS_8({
    ...{ class: "summary-card" },
}));
const __VLS_10 = __VLS_9({
    ...{ class: "summary-card" },
}, ...__VLS_functionalComponentArgsRest(__VLS_9));
__VLS_11.slots.default;
{
    const { title: __VLS_thisSlot } = __VLS_11.slots;
}
{
    const { content: __VLS_thisSlot } = __VLS_11.slots;
    if (__VLS_ctx.world?.recommended_targets?.length) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "target-list" },
        });
        for (const [target] of __VLS_getVForSourceType((__VLS_ctx.world.recommended_targets.slice(0, 8)))) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                key: (`${target.position.x}-${target.position.y}`),
                ...{ class: "target-item" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
            __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (target.position.x);
            (target.position.y);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({});
            (target.reason);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "target-score" },
            });
            const __VLS_12 = {}.Tag;
            /** @type {[typeof __VLS_components.Tag, ]} */ ;
            // @ts-ignore
            const __VLS_13 = __VLS_asFunctionalComponent(__VLS_12, new __VLS_12({
                severity: (target.boosted ? 'success' : target.threatened ? 'warn' : 'secondary'),
                value: (target.kind),
            }));
            const __VLS_14 = __VLS_13({
                severity: (target.boosted ? 'success' : target.threatened ? 'warn' : 'secondary'),
                value: (target.kind),
            }, ...__VLS_functionalComponentArgsRest(__VLS_13));
            __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (target.score.toFixed(1));
        }
    }
    else {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
            ...{ class: "empty-state" },
        });
    }
}
var __VLS_11;
const __VLS_16 = {}.Card;
/** @type {[typeof __VLS_components.Card, typeof __VLS_components.Card, ]} */ ;
// @ts-ignore
const __VLS_17 = __VLS_asFunctionalComponent(__VLS_16, new __VLS_16({
    ...{ class: "summary-card" },
}));
const __VLS_18 = __VLS_17({
    ...{ class: "summary-card" },
}, ...__VLS_functionalComponentArgsRest(__VLS_17));
__VLS_19.slots.default;
{
    const { title: __VLS_thisSlot } = __VLS_19.slots;
}
{
    const { content: __VLS_thisSlot } = __VLS_19.slots;
    if (__VLS_ctx.world?.planned_relocate_main) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "compact-item emphasis-item" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        (__VLS_ctx.world.planned_relocate_main.from_position.x);
        (__VLS_ctx.world.planned_relocate_main.from_position.y);
        (__VLS_ctx.world.planned_relocate_main.to_position.x);
        (__VLS_ctx.world.planned_relocate_main.to_position.y);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
        (__VLS_ctx.world.planned_relocate_main.reason);
    }
    if (__VLS_ctx.world?.intents?.length) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "compact-list top-gap" },
        });
        for (const [intent] of __VLS_getVForSourceType((__VLS_ctx.world.intents.slice(0, 10)))) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                key: (intent.id),
                ...{ class: "compact-item" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (intent.kind);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            (intent.summary);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
            (intent.priority);
            (intent.source);
            (intent.reason);
        }
    }
    else {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
            ...{ class: "empty-state" },
        });
    }
    if (__VLS_ctx.world?.planned_actions?.length) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "compact-list top-gap" },
        });
        for (const [action] of __VLS_getVForSourceType((__VLS_ctx.world.planned_actions.slice(0, 8)))) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                key: (`${action.author_id}-${action.kind}-${action.target_position.x}-${action.target_position.y}`),
                ...{ class: "compact-item" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
            (action.kind);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            (action.author_id);
            (action.target_position.x);
            (action.target_position.y);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.small, __VLS_intrinsicElements.small)({});
            (action.exit_position.x);
            (action.exit_position.y);
            (action.estimated_power);
        }
    }
}
var __VLS_19;
const __VLS_20 = {}.Card;
/** @type {[typeof __VLS_components.Card, typeof __VLS_components.Card, ]} */ ;
// @ts-ignore
const __VLS_21 = __VLS_asFunctionalComponent(__VLS_20, new __VLS_20({
    ...{ class: "summary-card" },
}));
const __VLS_22 = __VLS_21({
    ...{ class: "summary-card" },
}, ...__VLS_functionalComponentArgsRest(__VLS_21));
__VLS_23.slots.default;
{
    const { title: __VLS_thisSlot } = __VLS_23.slots;
}
{
    const { content: __VLS_thisSlot } = __VLS_23.slots;
    if (__VLS_ctx.world?.last_submission) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "summary-lines" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "summary-line" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        const __VLS_24 = {}.Tag;
        /** @type {[typeof __VLS_components.Tag, ]} */ ;
        // @ts-ignore
        const __VLS_25 = __VLS_asFunctionalComponent(__VLS_24, new __VLS_24({
            severity: (__VLS_ctx.world.last_submission.accepted ? 'success' : 'danger'),
            value: (__VLS_ctx.world.last_submission.dry_run ? 'dry-run' : 'sent'),
        }));
        const __VLS_26 = __VLS_25({
            severity: (__VLS_ctx.world.last_submission.accepted ? 'success' : 'danger'),
            value: (__VLS_ctx.world.last_submission.dry_run ? 'dry-run' : 'sent'),
        }, ...__VLS_functionalComponentArgsRest(__VLS_25));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "summary-line" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
        (__VLS_ctx.world.last_submission.errors.length);
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "pipeline-list top-gap" },
    });
    for (const [step] of __VLS_getVForSourceType((__VLS_ctx.world?.pipeline_steps ?? []))) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            key: (step.name),
            ...{ class: "pipeline-item" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "pipeline-topline" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
        (step.name);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "inline-stack" },
        });
        const __VLS_28 = {}.Tag;
        /** @type {[typeof __VLS_components.Tag, ]} */ ;
        // @ts-ignore
        const __VLS_29 = __VLS_asFunctionalComponent(__VLS_28, new __VLS_28({
            severity: (__VLS_ctx.pipelineSeverity(step.status)),
            value: (step.status),
        }));
        const __VLS_30 = __VLS_29({
            severity: (__VLS_ctx.pipelineSeverity(step.status)),
            value: (step.status),
        }, ...__VLS_functionalComponentArgsRest(__VLS_29));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        (step.duration_ms.toFixed(2));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({});
        (step.summary);
    }
}
var __VLS_23;
/** @type {__VLS_StyleScopedClasses['plan-board']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-card']} */ ;
/** @type {__VLS_StyleScopedClasses['alert-list']} */ ;
/** @type {__VLS_StyleScopedClasses['alert-item']} */ ;
/** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
/** @type {__VLS_StyleScopedClasses['highlight-list']} */ ;
/** @type {__VLS_StyleScopedClasses['top-gap']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-card']} */ ;
/** @type {__VLS_StyleScopedClasses['target-list']} */ ;
/** @type {__VLS_StyleScopedClasses['target-item']} */ ;
/** @type {__VLS_StyleScopedClasses['target-score']} */ ;
/** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-card']} */ ;
/** @type {__VLS_StyleScopedClasses['compact-item']} */ ;
/** @type {__VLS_StyleScopedClasses['emphasis-item']} */ ;
/** @type {__VLS_StyleScopedClasses['compact-list']} */ ;
/** @type {__VLS_StyleScopedClasses['top-gap']} */ ;
/** @type {__VLS_StyleScopedClasses['compact-item']} */ ;
/** @type {__VLS_StyleScopedClasses['empty-state']} */ ;
/** @type {__VLS_StyleScopedClasses['compact-list']} */ ;
/** @type {__VLS_StyleScopedClasses['top-gap']} */ ;
/** @type {__VLS_StyleScopedClasses['compact-item']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-card']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-lines']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['summary-line']} */ ;
/** @type {__VLS_StyleScopedClasses['pipeline-list']} */ ;
/** @type {__VLS_StyleScopedClasses['top-gap']} */ ;
/** @type {__VLS_StyleScopedClasses['pipeline-item']} */ ;
/** @type {__VLS_StyleScopedClasses['pipeline-topline']} */ ;
/** @type {__VLS_StyleScopedClasses['inline-stack']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            Card: Card,
            Tag: Tag,
            alertSeverity: alertSeverity,
            pipelineSeverity: pipelineSeverity,
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
