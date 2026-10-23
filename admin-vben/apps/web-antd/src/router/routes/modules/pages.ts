import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    component: () => import('#/views/pages/index.vue'),
    meta: { icon: 'lucide:file-text', title: '页面内容', order: 40 },
    name: 'Pages',
    path: '/pages',
  },
];

export default routes;
