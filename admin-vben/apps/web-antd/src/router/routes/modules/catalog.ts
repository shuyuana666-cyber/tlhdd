import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    component: () => import('#/views/catalog/index.vue'),
    meta: { icon: 'lucide:clipboard-list', title: '分类标签', order: 50 },
    name: 'CatalogTerms',
    path: '/catalog',
  },
];

export default routes;
