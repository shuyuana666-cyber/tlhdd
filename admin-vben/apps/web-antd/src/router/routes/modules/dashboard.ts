import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    component: () => import('#/views/dashboard/index.vue'),
    meta: { icon: 'lucide:layout-dashboard', affixTab: true, order: -1, title: '运营总览' },
    name: 'Dashboard',
    path: '/dashboard',
  },
];

export default routes;
