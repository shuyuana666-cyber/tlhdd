<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';

import { Button, Card, Popconfirm, Space, Spin, Table, Tag, message } from 'ant-design-vue';

import { deleteAdminResource, getAdminSnapshot } from '#/api';

const loading = ref(false);
const terms = ref<Record<string, any>[]>([]);
const columns = [
  { dataIndex: 'scope', key: 'scope', title: '适用范围' },
  { dataIndex: 'term_type', key: 'term_type', title: '类型' },
  { dataIndex: 'label_zh', key: 'label_zh', title: '显示名称' },
  { dataIndex: 'term_key', key: 'term_key', title: '系统标识' },
  { dataIndex: 'is_system', key: 'is_system', title: '属性' },
  { dataIndex: 'is_active', key: 'is_active', title: '状态' },
  { key: 'action', title: '操作' },
];
const count = computed(() => terms.value.length);

async function load() {
  loading.value = true;
  try {
    const result = await getAdminSnapshot();
    terms.value = result.catalog_terms || [];
  } catch (error: any) {
    message.error(error?.message || '分类标签加载失败');
  } finally {
    loading.value = false;
  }
}

async function remove(record: Record<string, any>) {
  try {
    await deleteAdminResource('catalog-terms', Number(record.id));
    terms.value = terms.value.filter((item) => Number(item.id) !== Number(record.id));
    message.success('分类标签已从数据库永久删除');
  } catch (error: any) {
    message.error(error?.message || '分类标签删除失败');
  }
}

onMounted(load);
</script>

<template>
  <Page description="管理车辆和配件使用的分类及标签，不在此处编辑商品记录" title="分类标签">
    <Card>
      <div class="mb-4 flex items-center justify-between">
        <span class="text-gray-500">共 {{ count }} 个分类 / 标签</span>
        <Button :loading="loading" @click="load">刷新</Button>
      </div>
      <Spin :spinning="loading">
        <Table :columns="columns" :data-source="terms" :pagination="{ pageSize: 20 }" :row-key="(row: any) => row.id" :scroll="{ x: 950 }">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'label_zh'">
              <strong>{{ record.label_zh || record.label_en || record.term_key }}</strong>
            </template>
            <template v-else-if="column.key === 'term_type'">
              <Tag>{{ record.term_type === 'category' ? '分类' : '标签' }}</Tag>
            </template>
            <template v-else-if="column.key === 'is_system'">
              <Tag :color="record.is_system ? 'blue' : 'default'">{{ record.is_system ? '内置项' : '自定义项' }}</Tag>
            </template>
            <template v-else-if="column.key === 'is_active'">
              <Tag :color="record.is_active ? 'green' : 'default'">{{ record.is_active ? '启用' : '停用' }}</Tag>
            </template>
            <template v-else-if="column.key === 'action'">
              <Space>
                <Popconfirm
                  :title="`永久删除“${record.label_zh || record.term_key}”？相关车辆或配件记录不会被删除。此操作无法撤销。`"
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
