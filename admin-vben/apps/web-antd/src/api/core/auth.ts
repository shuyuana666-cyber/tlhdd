import { requestClient } from '#/api/request';

export namespace AuthApi {
  /** 登录接口参数 */
  export interface LoginParams {
    password?: string;
    username?: string;
  }

  /** 登录接口返回值 */
  export interface LoginResult {
    user: Record<string, any>;
  }
}

/**
 * 登录
 */
export async function loginApi(data: AuthApi.LoginParams) {
  return requestClient.post<AuthApi.LoginResult>('/admin/login', {
    username: data.username,
    password: data.password,
  });
}

/**
 * 退出登录
 */
export async function logoutApi() {
  return requestClient.post('/admin/logout');
}

/**
 * 获取用户权限码
 */
export async function getAccessCodesApi() {
  return Promise.resolve(['admin']);
}
