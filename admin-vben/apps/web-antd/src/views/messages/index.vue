<script lang="ts" setup>
import { onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';

import { Button, Card, Input, Popconfirm, Select, Space, Spin, Table, Tag, message } from 'ant-design-vue';

import { deleteAdminResource, getAdminMessages, updateAdminMessage } from '#/api';

const loading = ref(false);
const search = ref('');
const status = ref('');
const threads = ref<Record<string, any>[]>([]);
const messageStatuses = [
  { label: '待回复', value: 'open' },
  { label: '跟进中', value: 'follow_up' },
  { label: '已处理', value: 'closed' },
];
const columns = [
  { dataIndex: 'contact_name', key: 'contact_name', title: '客户' },
  { dataIndex: 'contact_info', key: 'contact_info', title: '联系方式' },
  { dataIndex: 'subject', key: 'subject', title: '主题 / 商品' },
  { dataIndex: 'last_message', key: 'last_message', title: '最近消息' },
  { dataIndex: 'status', key: 'status', title: '状态' },
  { dataIndex: 'updated_at', key: 'updated_at', title: '更新时间' },
  { key: 'action', title: '操作' },
];

function shortText(value: unknown, length = 52) {
  const text = String(value || '-');
  return text.length > length ? `${text.slice(0, length)}…` : text;
}

async function load() {
  loading.value = true;
  try {
    const result = await getAdminMessages({ q: search.value.trim() || undefined, status: status.value || undefined });
    threads.value = result.threads || [];
  } catch (error: any) {
    message.error(error?.message || '在线消息加载失败');
  } finally {
    loading.value = false;
  }
}

async function changeStatus(record: Record<string, any>, nextStatus: string) {
  try {
    await updateAdminMessage(Number(record.id), { status: nextStatus });
    record.status = nextStatus;
    message.success('消息状态已更新');
  } catch (error: any) {
    message.error(error?.message || '状态更新失败');
  }
}

async function remove(record: Record<string, any>) {
  try {
    await deleteAdminResource('messages', Number(record.id));
    threads.value = threads.value.filter((item) => Number(item.id) !== Number(record.id));
    message.success('消息会话及全部聊天记录已永久删除');
  } catch (error: any) {
    message.error(error?.message || '消息删除失败');
  }
}

onMounted(load);
</script>

<template>
  <Page description="查看和跟进网站访客的在线咨询对话" title="在线消息">
    <Card>
      <Space class="mb-4" wrap>
        <Input.Search v-model:value="search" allow-clear placeholder="搜索客户、联系方式、商品或消息" style="width: 330px" @search="load" />
        <Select v-model:value="status" allow-clear placeholder="全部状态" style="width: 150px" @change="load">
          <Select.Option v-for="item in messageStatuses" :key="item.value" :value="item.value">{{ item.label }}</Select.Option>
        </Select>
        <Button @click="load">刷新</Button>
        <span class="text-gray-500">共 {{ threads.length }} 个会话</span>
      </Space>
      <Spin :spinning="loading">
        <Table :columns="columns" :data-source="threads" :pagination="{ pageSize: 15 }" :row-key="(row: any) => row.id" :scroll="{ x: 1200 }">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'contact_name'">
              <strong>{{ record.contact_name || '访客' }}</strong>
            </template>
            <template v-else-if="column.key === 'subject'">
              {{ record.product_title || record.subject || '在线咨询' }}
            </template>
            <template v-else-if="column.key === 'last_message'">
              {{ shortText(record.last_message || record.preview || record.message) }}
            </template>
            <template v-else-if="column.key === 'status'">
              <Tag :color="record.status === 'open' ? 'red' : record.status === 'follow_up' ? 'orange' : 'green'">
                {{ messageStatuses.find((item) => item.value === record.status)?.label || record.status }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'action'">
              <Space>
                <Select :value="record.status" size="small" style="width: 110px" @change="(value: any) => changeStatus(record, String(value || ''))">
                  <Select.Option v-for="item in messageStatuses" :key="item.value" :value="item.value">{{ item.label }}</Select.Option>
                </Select>
                <Popconfirm title="永久删除此会话及其全部聊天记录？此操作无法撤销。" @confirm="remove(record)">
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
