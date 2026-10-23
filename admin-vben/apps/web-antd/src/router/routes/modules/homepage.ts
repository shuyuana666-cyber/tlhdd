import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    component: () => import('#/views/homepage/index.vue'),
    meta: { icon: 'lucide:images', title: '页面配置', order: 30 },
    name: 'Homepage',
    path: '/homepage',
  },
];

export default routes;
