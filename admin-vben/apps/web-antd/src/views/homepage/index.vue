<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';

import { Button, Card, Popconfirm, Space, Spin, Switch, Table, Tabs, message } from 'ant-design-vue';

import { deleteAdminResource, getAdminSnapshot, saveAdminResource, uploadAdminMedia } from '#/api';
import AdminImageActions from '#/components/AdminImageActions.vue';

const activeKey = ref('slides');
const loading = ref(false);
const snapshot = ref<Record<string, any>>({});
const uploadingKey = ref('');

const tabs = [
  { key: 'slides', label: '首页轮播', source: 'hero_slides', resource: 'slides' },
  { key: 'metrics', label: '首页数据指标', source: 'home_metrics', resource: 'metrics' },
  { key: 'sections', label: '首页内容区块', source: '', resource: 'page-sections' },
  { key: 'items', label: '首页区块内容项', source: '', resource: 'page-section-items' },
  { key: 'media', label: '首页素材', source: '', resource: 'page-media' },
];

const activeTab = computed(() => tabs.find((tab) => tab.key === activeKey.value) || tabs[0]!);
const homeSections = computed(() => (snapshot.value.page_sections || []).filter((row: Record<string, any>) => row.page_key === 'index'));
const rows = computed(() => {
  if (activeKey.value === 'sections') return homeSections.value;
  if (activeKey.value === 'items') {
    return homeSections.value.flatMap((section: Record<string, any>) =>
      (section.items || []).map((item: Record<string, any>) => ({
        ...item,
        parent_label: section.label || section.section_key,
      })),
    );
  }
  if (activeKey.value === 'media') {
    return (snapshot.value.page_media || []).filter((row: Record<string, any>) => row.page_key === 'home');
  }
  return snapshot.value[activeTab.value.source || ''] || [];
});
const columns = computed(() => {
  if (activeKey.value === 'slides') {
    return [
      { dataIndex: 'title_zh', key: 'title_zh', title: '中文标题' },
      { dataIndex: 'lead_zh', key: 'lead_zh', title: '中文说明' },
      { dataIndex: 'image_url', key: 'image_url', title: '配图' },
      { dataIndex: 'sort_order', key: 'sort_order', title: '排序' },
      { dataIndex: 'is_active', key: 'is_active', title: '启用状态' },
      { key: 'action', title: '操作' },
    ];
  }
  if (activeKey.value === 'metrics') {
    return [
      { dataIndex: 'label', key: 'label', title: '指标名称' },
      { dataIndex: 'value', key: 'value', title: '指标值' },
      { dataIndex: 'sort_order', key: 'sort_order', title: '排序' },
      { dataIndex: 'is_active', key: 'is_active', title: '启用状态' },
      { key: 'action', title: '操作' },
    ];
  }
  if (activeKey.value === 'sections') {
    return [
      { dataIndex: 'section_key', key: 'section_key', title: '区块标识' },
      { dataIndex: 'label', key: 'label', title: '区块名称' },
      { dataIndex: 'title_zh', key: 'title_zh', title: '中文标题' },
      { dataIndex: 'image_url', key: 'image_url', title: '配图' },
      { dataIndex: 'sort_order', key: 'sort_order', title: '排序' },
      { dataIndex: 'is_active', key: 'is_active', title: '状态' },
      { key: 'action', title: '操作' },
    ];
  }
  if (activeKey.value === 'items') {
    return [
      { dataIndex: 'parent_label', key: 'parent_label', title: '所属区块' },
      { dataIndex: 'title_zh', key: 'title_zh', title: '内容标题' },
      { dataIndex: 'image_url', key: 'image_url', title: '配图' },
      { dataIndex: 'sort_order', key: 'sort_order', title: '排序' },
      { dataIndex: 'is_active', key: 'is_active', title: '状态' },
      { key: 'action', title: '操作' },
    ];
  }
  return [
    { dataIndex: 'label', key: 'label', title: '素材名称' },
    { dataIndex: 'media_key', key: 'media_key', title: '素材标识' },
    { dataIndex: 'image_url', key: 'image_url', title: '素材地址' },
    { dataIndex: 'is_active', key: 'is_active', title: '状态' },
    { key: 'action', title: '操作' },
  ];
});

function isEnabled(value: unknown) {
  return value === true || value === 1 || value === '1';
}

async function load() {
  loading.value = true;
  try {
    snapshot.value = await getAdminSnapshot();
  } catch (error: any) {
    message.error(error?.message || '页面配置加载失败');
  } finally {
    loading.value = false;
  }
}

async function toggleActive(record: Record<string, any>, value: any) {
  const isActive = value === true || value === 'true';
  try {
    await saveAdminResource(activeTab.value.resource, { ...record, is_active: isActive }, Number(record.id));
    record.is_active = isActive ? 1 : 0;
    message.success('页面配置状态已更新');
  } catch (error: any) {
    message.error(error?.message || '状态更新失败');
  }
}

async function remove(record: Record<string, any>) {
  try {
    await deleteAdminResource(activeTab.value.resource, Number(record.id));
    await load();
    message.success('配置记录已永久删除');
  } catch (error: any) {
    message.error(error?.message || '删除失败');
  }
}

function switchTab(key: string | number) {
  activeKey.value = String(key);
}

function imageKey(record: Record<string, any>) {
  return `${activeTab.value.resource}:${record.id}`;
}

async function replaceImage(record: Record<string, any>, file: File) {
  const resource = activeTab.value.resource;
  const id = Number(record.id);
  const key = `${resource}:${id}`;
  if (file.size > 20 * 1024 * 1024) {
    message.error('单张图片不能超过 20MB');
    return;
  }
  uploadingKey.value = key;
  try {
    const uploaded = await uploadAdminMedia(file);
    const imageUrl = uploaded.optimized_url || uploaded.url;
    await saveAdminResource(
      resource,
      { ...record, image_url: imageUrl, ...(resource === 'page-media' ? { is_active: true } : {}) },
      id,
    );
    await load();
    message.success('图片已替换');
  } catch (error: any) {
    message.error(error?.message || '图片替换失败');
  } finally {
    uploadingKey.value = '';
  }
}

async function clearImage(record: Record<string, any>) {
  const resource = activeTab.value.resource;
  try {
    await saveAdminResource(
      resource,
      { ...record, image_url: '', ...(resource === 'page-media' ? { is_active: false } : {}) },
      Number(record.id),
    );
    await load();
    message.success('图片已删除');
  } catch (error: any) {
    message.error(error?.message || '图片删除失败');
  }
}

async function restoreDefaultImage(record: Record<string, any>) {
  try {
    await saveAdminResource('page-media', { restore: true }, Number(record.id));
    await load();
    message.success('已还原默认图片');
  } catch (error: any) {
    message.error(error?.message || '默认图片还原失败');
  }
}

onMounted(load);
</script>

<template>
    <Page description="维护首页内容，并替换、删除或还原网站各页面的图片" title="页面配置">
    <Card>
      <div class="mb-4 flex items-center justify-between">
        <span class="text-gray-500">当前 {{ activeTab.label }}：{{ rows.length }} 条</span>
        <Button :loading="loading" @click="load">刷新</Button>
      </div>
      <Tabs :active-key="activeKey" @change="switchTab">
        <Tabs.TabPane v-for="tab in tabs" :key="tab.key" :tab="tab.label" />
      </Tabs>
      <Spin :spinning="loading">
        <Table :columns="columns" :data-source="rows" :pagination="{ pageSize: 12 }" :row-key="(row: any) => row.id" :scroll="{ x: 900 }">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'title' || column.key === 'title_zh'">
              <strong>{{ record.title || record.title_zh || '-' }}</strong>
            </template>
            <template v-else-if="column.key === 'image_url'">
              <AdminImageActions
                :image-url="record.image_url"
                :default-url="record.default_url"
                :loading="uploadingKey === imageKey(record)"
                @replace="(file: File) => replaceImage(record, file)"
                @clear="clearImage(record)"
                @restore="restoreDefaultImage(record)"
              />
            </template>
            <template v-else-if="column.key === 'label'">
              {{ record.label || record.label_zh || '-' }}
            </template>
            <template v-else-if="column.key === 'is_active'">
              <Switch :checked="isEnabled(record.is_active)" checked-children="启用" un-checked-children="停用" @change="(value: any) => toggleActive(record, value)" />
            </template>
            <template v-else-if="column.key === 'action'">
              <Space>
                <Popconfirm
                  :title="activeKey === 'media' ? '永久删除这个页面素材位？页面图片将停止显示。此操作无法撤销。' : '永久删除这条首页配置？此操作无法撤销。'"
                  @confirm="remove(record)"
                >
                  <Button danger size="small" type="link">删除</Button>
                </Popconfirm>
              </Space>
            </template>
          </template>
        </Table>
      </Spin>
    </Card>
  </Page>
</template>
