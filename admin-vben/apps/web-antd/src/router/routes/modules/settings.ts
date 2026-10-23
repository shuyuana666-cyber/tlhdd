import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    component: () => import('#/views/settings/index.vue'),
    meta: { icon: 'lucide:settings', title: '系统设置', order: 90 },
    name: 'Settings',
    path: '/settings',
  },
];

export default routes;
