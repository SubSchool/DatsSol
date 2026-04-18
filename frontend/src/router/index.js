import { createRouter, createWebHistory } from 'vue-router';
const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/',
            redirect: '/visualization',
        },
        {
            path: '/visualization',
            name: 'visualization',
            component: () => import('@/views/VisualizationView.vue'),
        },
        {
            path: '/logs',
            name: 'logs',
            component: () => import('@/views/LogsView.vue'),
        },
    ],
});
export default router;
