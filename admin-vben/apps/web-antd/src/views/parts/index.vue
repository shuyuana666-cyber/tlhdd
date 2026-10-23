<script lang="ts" setup>
import { onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Input,
  message,
  Popconfirm,
  Select,
  Spin,
  Switch,
  Table,
} from 'ant-design-vue';

import { deleteAdminResource, getAdminParts, saveAdminResource } from '#/api';
import InventoryToolbar from '#/components/InventoryToolbar.vue';

import { useInventorySelection } from '../shared/use-inventory-selection';

const loading = ref(false);
const search = ref('');
const status = ref('');
const rows = ref<Record<string, any>[]>([]);
const pagination = ref({ current: 1, pageSize: 50, total: 0 });

const { cancelSelection, clearSelection, confirmDelete, deleting, rowSelection, selectedIds, selecting } =
  useInventorySelection('parts', '配件', load);

const columns = [
  { dataIndex: 'title', key: 'title', title: '配件名称' },
  { dataIndex: 'part_no', key: 'part_no', title: '配件编号' },
  { dataIndex: 'category_zh', key: 'category_zh', title: '分类' },
  { dataIndex: 'price', key: 'price', title: '价格' },
  { dataIndex: 'is_active', key: 'is_active', title: '上架状态' },
  { key: 'action', title: '操作' },
];

function isEnabled(value: unknown) {
  return value === true || value === 1 || value === '1';
}

async function load() {
  clearSelection();
  loading.value = true;
  try {
    const result = await getAdminParts({
      page: pagination.value.current,
      page_size: pagination.value.pageSize,
      q: search.value.trim() || undefined,
      status: status.value || undefined,
    });
    rows.value = result.parts || [];
    pagination.value = {
      current: Number(result.pagination.page || 1),
      pageSize: Number(result.pagination.page_size || 50),
      total: Number(result.pagination.total || 0),
    };
  } catch (error: any) {
    message.error(error?.message || '配件加载失败');
  } finally {
    loading.value = false;
  }
}

function applyFilters() {
  pagination.value.current = 1;
  load();
}

function changePage(pager: Record<string, number>) {
  pagination.value.current = pager.current || 1;
  pagination.value.pageSize = pager.pageSize || 50;
  load();
}

async function toggleActive(record: Record<string, any>, value: any) {
  const isActive = value === true || value === 'true';
  try {
    await saveAdminResource('parts', { ...record, is_active: isActive }, Number(record.id));
    record.is_active = isActive ? 1 : 0;
    message.success('配件状态已更新');
  } catch (error: any) {
    message.error(error?.message || '配件状态更新失败');
  }
}

async function remove(record: Record<string, any>) {
  try {
    await deleteAdminResource('parts', Number(record.id));
    message.success('配件及其数据库记录已永久删除');
    if (rows.value.length === 1 && pagination.value.current > 1) {
      pagination.value.current -= 1;
    }
    await load();
  } catch (error: any) {
    message.error(error?.message || '配件删除失败');
  }
}

onMounted(load);
</script>

<template>
  <Page description="单独维护配件目录与上架状态" title="配件管理">
    <Card>
      <InventoryToolbar
        label="配件筛选与操作"
        :hint="selecting ? '可多选当前页记录，翻页或筛选后重新选择' : undefined"
      >
        <template #filters>
          <Input.Search
            v-model:value="search"
            :disabled="deleting"
            allow-clear
            placeholder="搜索名称、编号、品牌或适配车型"
            aria-label="搜索配件名称、编号、品牌或适配车型"
            @search="applyFilters"
          />
          <Select :disabled="deleting" v-model:value="status" allow-clear aria-label="筛选配件状态" placeholder="全部状态" @change="applyFilters">
            <Select.Option value="">全部状态</Select.Option>
            <Select.Option value="active">已上架</Select.Option>
            <Select.Option value="inactive">已停用</Select.Option>
            <Select.Option value="featured">推荐配件</Select.Option>
            <Select.Option value="missing_image">缺少图片</Select.Option>
          </Select>
        </template>
        <template #actions>
          <Button :disabled="deleting" @click="load">刷新</Button>
          <Button v-if="!selecting" danger @click="selecting = true">批量删除</Button>
          <template v-else>
            <Button danger type="primary" :disabled="!selectedIds.length || loading" :loading="deleting" @click="confirmDelete">
              删除选中（{{ selectedIds.length }}）
            </Button>
            <Button :disabled="deleting" @click="cancelSelection">取消多选</Button>
          </template>
        </template>
        <template #summary>共 {{ pagination.total }} 件</template>
      </InventoryToolbar>
      <Spin :spinning="loading">
        <Table
          :columns="columns"
          :row-selection="rowSelection"
          :data-source="rows"
          :pagination="{ ...pagination, disabled: deleting, showSizeChanger: true, pageSizeOptions: ['20', '50', '100'] }"
          :row-key="(row: any) => row.id"
          :scroll="{ x: 900 }"
          @change="(pager: any) => changePage(pager)"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'is_active'">
              <Switch
                :checked="isEnabled(record.is_active)"
                :disabled="deleting"
                checked-children="上架"
                un-checked-children="停用"
                @change="(value: any) => toggleActive(record, value)"
              />
            </template>
            <template v-else-if="column.key === 'action'">
              <Popconfirm
                :disabled="deleting"
                title="永久删除此配件及其数据库记录？此操作无法撤销。"
                @confirm="remove(record)"
              >
                <Button :disabled="deleting" danger size="small" type="link">删除</Button>
              </Popconfirm>
            </template>
          </template>
        </Table>
      </Spin>
    </Card>
  </Page>
</template>
