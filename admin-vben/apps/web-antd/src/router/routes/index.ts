import type { RouteRecordRaw } from 'vue-router';

import { traverseTreeValues } from '@vben/utils';

import { coreRoutes, fallbackNotFoundRoute } from './core';
import catalogRoutes from './modules/catalog';
import dashboardRoutes from './modules/dashboard';
import inquiriesRoutes from './modules/inquiries';
import messagesRoutes from './modules/messages';
import newsRoutes from './modules/news';
import pageManagementRoutes from './modules/page-management';
import partsRoutes from './modules/parts';
import settingsRoutes from './modules/settings';
import usersRoutes from './modules/users';
import vehiclesRoutes from './modules/vehicles';

const accessRoutes: RouteRecordRaw[] = [
  ...dashboardRoutes,
  ...vehiclesRoutes,
  ...partsRoutes,
  ...pageManagementRoutes,
  ...newsRoutes,
  ...catalogRoutes,
  ...inquiriesRoutes,
  ...messagesRoutes,
  ...usersRoutes,
  ...settingsRoutes,
];

const routes: RouteRecordRaw[] = [...coreRoutes, fallbackNotFoundRoute];
const coreRouteNames = traverseTreeValues(coreRoutes, (route) => route.name);

export { accessRoutes, coreRouteNames, routes };
