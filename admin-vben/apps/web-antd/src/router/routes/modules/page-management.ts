import type { RouteRecordRaw } from 'vue-router';

import homepageRoutes from './homepage';
import pagesRoutes from './pages';

const routes: RouteRecordRaw[] = [
  {
    children: [...homepageRoutes, ...pagesRoutes],
    meta: { title: '页面管理', icon: 'lucide:file-stack', order: 30 },
    name: 'PageManagement',
    path: '/page-management',
    redirect: '/homepage',
  },
];

export default routes;
