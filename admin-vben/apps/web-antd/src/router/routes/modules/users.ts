import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    component: () => import('#/views/users/index.vue'),
    meta: { icon: 'lucide:users', title: '注册用户', order: 80 },
    name: 'Users',
    path: '/users',
  },
];

export default routes;
