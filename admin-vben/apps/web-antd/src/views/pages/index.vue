<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';

import { Button, Card, Popconfirm, Space, Spin, Table, Tabs, Tag, message } from 'ant-design-vue';

import { deleteAdminResource, getAdminSnapshot, saveAdminResource, uploadAdminMedia } from '#/api';
import AdminImageActions from '#/components/AdminImageActions.vue';

const activeKey = ref('sections');
const loading = ref(false);
const snapshot = ref<Record<string, any>>({});
const uploadingKey = ref('');

const sections = computed(() => (snapshot.value.page_sections || []).filter((section: Record<string, any>) => section.page_key !== 'index'));
const rows = computed(() => {
  if (activeKey.value === 'items') {
    return sections.value.flatMap((section: Record<string, any>) =>
      (section.items || []).map((item: Record<string, any>) => ({
        ...item,
        parent_label: section.label || `${section.page_key} / ${section.section_key}`,
      })),
    );
  }
  return activeKey.value === 'media'
    ? (snapshot.value.page_media || []).filter((item: Record<string, any>) => item.page_key !== 'home')
    : sections.value;
});

const resource = computed(() => ({
  sections: 'page-sections',
  items: 'page-section-items',
  media: 'page-media',
}[activeKey.value] || 'page-sections'));

const columns = computed(() => {
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
  if (activeKey.value === 'media') {
    return [
      { dataIndex: 'page_key', key: 'page_key', title: '所属页面' },
      { dataIndex: 'label', key: 'label', title: '素材名称' },
      { dataIndex: 'media_key', key: 'media_key', title: '素材标识' },
      { dataIndex: 'image_url', key: 'image_url', title: '素材地址' },
      { dataIndex: 'is_active', key: 'is_active', title: '状态' },
      { key: 'action', title: '操作' },
    ];
  }
  return [
    { dataIndex: 'page_key', key: 'page_key', title: '所属页面' },
    { dataIndex: 'section_key', key: 'section_key', title: '区块标识' },
    { dataIndex: 'label', key: 'label', title: '区块名称' },
    { dataIndex: 'title_zh', key: 'title_zh', title: '中文标题' },
    { dataIndex: 'image_url', key: 'image_url', title: '配图' },
    { dataIndex: 'is_active', key: 'is_active', title: '状态' },
    { key: 'action', title: '操作' },
  ];
});

async function load() {
  loading.value = true;
  try {
    snapshot.value = await getAdminSnapshot();
  } catch (error: any) {
    message.error(error?.message || '页面内容加载失败');
  } finally {
    loading.value = false;
  }
}

async function remove(record: Record<string, any>) {
  try {
    await deleteAdminResource(resource.value, Number(record.id));
    await load();
    message.success('页面内容记录已永久删除');
  } catch (error: any) {
    message.error(error?.message || '删除失败');
  }
}

function imageKey(record: Record<string, any>) {
  return `${resource.value}:${record.id}`;
}

async function replaceImage(record: Record<string, any>, file: File) {
  const currentResource = resource.value;
  const id = Number(record.id);
  const key = `${currentResource}:${id}`;
  if (file.size > 20 * 1024 * 1024) {
    message.error('单张图片不能超过 20MB');
    return;
  }
  uploadingKey.value = key;
  try {
    const uploaded = await uploadAdminMedia(file);
    const imageUrl = uploaded.optimized_url || uploaded.url;
    await saveAdminResource(
      currentResource,
      { ...record, image_url: imageUrl, ...(currentResource === 'page-media' ? { is_active: true } : {}) },
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
  const currentResource = resource.value;
  try {
    await saveAdminResource(
      currentResource,
      { ...record, image_url: '', ...(currentResource === 'page-media' ? { is_active: false } : {}) },
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

function switchTab(key: string | number) {
  activeKey.value = String(key);
}

onMounted(load);
</script>

<template>
  <Page description="维护新车、二手车、公司介绍等页面区块和图片素材" title="页面内容">
    <Card>
      <div class="mb-4 flex items-center justify-between">
        <span class="text-gray-500">当前内容：{{ rows.length }} 条</span>
        <Button :loading="loading" @click="load">刷新</Button>
      </div>
      <Tabs :active-key="activeKey" @change="switchTab">
        <Tabs.TabPane key="sections" tab="页面区块" />
        <Tabs.TabPane key="items" tab="区块内容项" />
        <Tabs.TabPane key="media" tab="页面素材" />
      </Tabs>
      <Spin :spinning="loading">
        <Table :columns="columns" :data-source="rows" :pagination="{ pageSize: 15 }" :row-key="(row: any) => row.id" :scroll="{ x: 1000 }">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'image_url'">
              <AdminImageActions
                :image-url="record.image_url"
                :default-url="record.default_url"
                :loading="uploadingKey === imageKey(record)"
                @replace="(file: File) => replaceImage(record, file)"
                @clear="clearImage(record)"
                @restore="restoreDefaultImage(record)"
              />
            </template>
            <template v-if="column.key === 'is_active'">
              <Tag :color="record.is_active ? 'green' : 'default'">{{ record.is_active ? '启用' : '停用' }}</Tag>
            </template>
            <template v-else-if="column.key === 'action'">
              <Space>
                <Popconfirm
                  :title="activeKey === 'media' ? '永久删除这个页面素材位？页面图片将停止显示。此操作无法撤销。' : '永久删除这条页面记录？此操作无法撤销。'"
                  @confirm="remove(record)"
                >
                  <Button danger size="small" type="link">删除记录</Button>
                </Popconfirm>
              </Space>
            </template>
          </template>
        </Table>
      </Spin>
    </Card>
  </Page>
</template>
