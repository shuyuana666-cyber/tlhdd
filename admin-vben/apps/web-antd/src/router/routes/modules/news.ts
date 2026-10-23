import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    component: () => import('#/views/news/index.vue'),
    meta: { title: '新闻中心', icon: 'lucide:newspaper', order: 35 },
    name: 'News',
    path: '/news',
  },
];

export default routes;
