import { createApp, watchEffect } from 'vue';

import { registerAccessDirective } from '@vben/access';
import { registerLoadingDirective } from '@vben/common-ui/es/loading';
import { addIcon } from '@vben/icons';
import { preferences } from '@vben/preferences';
import { initStores } from '@vben/stores';
import '@vben/styles';
import '@vben/styles/antd';

import { useTitle } from '@vueuse/core';

import { $t, setupI18n } from '#/locales';

import { initComponentAdapter } from './adapter/component';
import { initSetupVbenForm } from './adapter/form';
import App from './app.vue';
import { registerNavigationIcons } from './navigation-icons';
import { router } from './router';


async function bootstrap(namespace: string) {
  registerNavigationIcons();
  // Bundle the layout controls so they work with the site's self-only CSP.
  const frame =
    '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18"/>';
  const stroke = (body: string) =>
    `<g fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${body}</g>`;
  addIcon('lucide:newspaper', {
    width: 24,
    height: 24,
    body: stroke(
      '<path d="M4 4h16v16a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8h2V4Z"/><path d="M4 8v12M8 8h8M8 12h8M8 16h3M14 16h2"/>',
    ),
  });
  addIcon('ep:fold', {
    width: 24,
    height: 24,
    body: stroke(`${frame}<path d="m16 9-3 3 3 3"/>`),
  });
  addIcon('ep:expand', {
    width: 24,
    height: 24,
    body: stroke(`${frame}<path d="m14 9 3 3-3 3"/>`),
  });
  addIcon('fluent-mdl2:world-clock', {
    width: 24,
    height: 24,
    body: stroke(
      '<circle cx="10" cy="10" r="7"/><path d="M3 10h14M10 3c-4 4-4 10 0 14M10 3c2 2 3 4 3 6"/><circle cx="17" cy="17" r="4"/><path d="M17 15v2h2"/>',
    ),
  });
  // 初始化组件适配器
  await initComponentAdapter();

  // 初始化表单组件
  await initSetupVbenForm();

  // // 设置弹窗的默认配置
  // setDefaultModalProps({
  //   fullscreenButton: false,
  // });
  // // 设置抽屉的默认配置
  // setDefaultDrawerProps({
  //   zIndex: 1020,
  // });

  const app = createApp(App);

  // 注册v-loading指令
  registerLoadingDirective(app, {
    loading: 'loading', // 在这里可以自定义指令名称，也可以明确提供false表示不注册这个指令
    spinning: 'spinning',
  });

  // 国际化 i18n 配置
  await setupI18n(app);

  // 配置 pinia-tore
  await initStores(app, { namespace });

  // 安装权限指令
  registerAccessDirective(app);

  // 初始化 tippy
  const { initTippy } = await import('@vben/common-ui/es/tippy');
  initTippy(app);

  // 配置路由及路由守卫
  app.use(router);

  // 配置Motion插件
  const { MotionPlugin } = await import('@vben/plugins/motion');
  app.use(MotionPlugin);

  // 动态更新标题
  watchEffect(() => {
    if (preferences.app.dynamicTitle) {
      const routeTitle = router.currentRoute.value.meta?.title;
      const pageTitle =
        (routeTitle ? `${$t(routeTitle)} - ` : '') + preferences.app.name;
      useTitle(pageTitle);
    }
  });

  app.mount('#app');
}

export { bootstrap };
