import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    component: () => import('#/views/parts/index.vue'),
    meta: { icon: 'lucide:wrench', title: '配件管理', order: 20 },
    name: 'Parts',
    path: '/parts',
  },
];

export default routes;
