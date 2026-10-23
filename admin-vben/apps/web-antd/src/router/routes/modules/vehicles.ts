import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    component: () => import('#/views/vehicles/index.vue'),
    meta: { icon: 'lucide:car-front', title: '车辆管理', order: 10 },
    name: 'Vehicles',
    path: '/vehicles',
  },
];

export default routes;
