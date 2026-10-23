import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    component: () => import('#/views/messages/index.vue'),
    meta: { icon: 'lucide:messages-square', title: '在线消息', order: 70 },
    name: 'Messages',
    path: '/messages',
  },
];

export default routes;
