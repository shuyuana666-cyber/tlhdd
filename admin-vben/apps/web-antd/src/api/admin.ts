import { requestClient } from '#/api/request';

async function patchRequest<T = any>(path: string, payload: Record<string, any>) {
  return requestClient.request<T>(path, {
    data: payload,
    method: 'PATCH',
  });
}

export interface AdminSnapshot {
  chat_threads: Record<string, any>[];
  catalog_terms: Record<string, any>[];
  dashboard_summary: Record<string, any>;
  hero_slides: Record<string, any>[];
  home_metrics: Record<string, any>[];
  inquiries: Record<string, any>[];
  page_media: Record<string, any>[];
  page_sections: Record<string, any>[];
  parts: Record<string, any>[];
  public_users: Record<string, any>[];
  settings: Record<string, any>;
  vehicles: Record<string, any>[];
  [key: string]: any;
}

export async function getAdminSnapshot() {
  return requestClient.get<AdminSnapshot>('/admin/all');
}

export async function getAdminNews(params?: { q?: string; status?: string }) {
  return requestClient.get<{ news: Record<string, any>[] }>('/admin/news', { params });
}

export async function getAdminSummary() {
  const result = await requestClient.get<{ summary: Record<string, any> }>(
    '/admin/summary',
  );
  return result.summary;
}

export async function getAdminVehicles(params?: {
  page?: number;
  page_size?: number;
  q?: string;
  status?: string;
  type?: string;
}) {
  return requestClient.get<{
    pagination: Record<string, number>;
    vehicles: Record<string, any>[];
  }>('/admin/vehicles', { params });
}

export async function getAdminParts(params?: {
  page?: number;
  page_size?: number;
  q?: string;
  status?: string;
}) {
  return requestClient.get<{
    pagination: Record<string, number>;
    parts: Record<string, any>[];
  }>('/admin/parts', { params });
}

export async function getAdminInquiries(params?: {
  q?: string;
  status?: string;
}) {
  return requestClient.get<{ inquiries: Record<string, any>[] }>(
    '/admin/inquiries',
    { params },
  );
}

export async function updateAdminInquiry(
  id: number,
  payload: Record<string, any>,
) {
  return patchRequest(`/admin/inquiries/${id}`, payload);
}

export async function getAdminMessages(params?: {
  q?: string;
  status?: string;
}) {
  return requestClient.get<{ threads: Record<string, any>[] }>(
    '/admin/messages',
    { params },
  );
}

export async function updateAdminMessage(
  id: number,
  payload: Record<string, any>,
) {
  return patchRequest(`/admin/messages/${id}`, payload);
}

export async function saveAdminSettings(payload: Record<string, any>) {
  return patchRequest<{ settings: Record<string, any> }>('/admin/settings', payload);
}

export async function changeAdminPassword(payload: Record<string, any>) {
  return requestClient.post('/admin/change-password', payload);
}

export async function deleteAdminResource(resource: string, id: number) {
  return requestClient.delete(`/admin/${resource}/${id}`);
}

export async function bulkDeleteInventory(resource: 'parts' | 'vehicles', ids: number[]) {
  return requestClient.post<{ deleted_count: number; ok: boolean }>(
    `/admin/${resource}/bulk-delete`, { ids },
  );
}

export interface AdminUploadedMedia {
  media_type: 'image' | 'video';
  optimized_url?: string;
  thumb_url?: string;
  url: string;
}

export async function uploadAdminMedia(file: File) {
  return requestClient.upload<AdminUploadedMedia>('/admin/upload-media', { file });
}

export async function saveAdminResource(
  resource: string,
  payload: Record<string, any>,
  id?: number,
) {
  const path = id ? `/admin/${resource}/${id}` : `/admin/${resource}`;
  return patchRequest(path, payload);
}
