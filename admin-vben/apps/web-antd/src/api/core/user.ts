import type { UserInfo } from '@vben/types';

import { requestClient } from '#/api/request';

/**
 * 获取用户信息
 */
export async function getUserInfoApi() {
  const response = await requestClient.get<{ user: Record<string, any> }>(
    '/admin/me',
  );
  const user = response.user || {};
  return {
    avatar: user.avatar_url || '',
    desc: '通利华汽车集团后台管理员',
    homePath: '/dashboard',
    realName: user.display_name || user.username || '管理员',
    roles: [user.permission || user.role || 'admin'],
    token: 'cookie-session',
    userId: String(user.id || user.user_id || ''),
    username: user.username || user.account || '',
  } as UserInfo;
}
