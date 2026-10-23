import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    component: () => import('#/views/inquiries/index.vue'),
    meta: { icon: 'lucide:message-square-text', title: '询盘管理', order: 60 },
    name: 'Inquiries',
    path: '/inquiries',
  },
];

export default routes;
