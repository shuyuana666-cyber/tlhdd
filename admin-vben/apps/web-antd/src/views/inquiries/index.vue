<script lang="ts" setup>
import { onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';

import { Button, Card, Input, Popconfirm, Select, Space, Spin, Table, Tag, message } from 'ant-design-vue';

import { deleteAdminResource, getAdminInquiries, updateAdminInquiry } from '#/api';

const loading = ref(false);
const search = ref('');
const status = ref('');
const inquiries = ref<Record<string, any>[]>([]);

const inquiryStatuses = ['新询盘', '跟进中', '已报价', '已关闭'];
const columns = [
  { dataIndex: 'name', key: 'name', title: '联系人' },
  { dataIndex: 'contact', key: 'contact', title: '联系方式' },
  { dataIndex: 'vehicle_interest', key: 'vehicle_interest', title: '意向车型 / 需求' },
  { dataIndex: 'destination', key: 'destination', title: '目的地' },
  { dataIndex: 'status', key: 'status', title: '状态' },
  { dataIndex: 'created_at', key: 'created_at', title: '提交时间' },
  { key: 'action', title: '操作' },
];

function statusColor(value: string) {
  return value === '新询盘' ? 'red' : value === '跟进中' ? 'orange' : value === '已报价' ? 'blue' : 'green';
}

async function load() {
  loading.value = true;
  try {
    const result = await getAdminInquiries({
      q: search.value.trim() || undefined,
      status: status.value || undefined,
    });
    inquiries.value = result.inquiries || [];
  } catch (error: any) {
    message.error(error?.message || '询盘加载失败');
  } finally {
    loading.value = false;
  }
}

async function changeStatus(record: Record<string, any>, nextStatus: string) {
  try {
    await updateAdminInquiry(Number(record.id), { status: nextStatus });
    record.status = nextStatus;
    message.success('询盘状态已更新');
  } catch (error: any) {
    message.error(error?.message || '状态更新失败');
  }
}

async function remove(record: Record<string, any>) {
  try {
    await deleteAdminResource('inquiries', Number(record.id));
    inquiries.value = inquiries.value.filter((item) => Number(item.id) !== Number(record.id));
    message.success('询盘已从数据库永久删除');
  } catch (error: any) {
    message.error(error?.message || '询盘删除失败');
  }
}

onMounted(load);
</script>

<template>
  <Page description="集中跟进客户提交的车型和服务需求" title="询盘管理">
    <Card>
      <Space class="mb-4" wrap>
        <Input.Search
          v-model:value="search"
          allow-clear
          placeholder="搜索联系人、联系方式、车型或目的地"
          style="width: 330px"
          @search="load"
        />
        <Select v-model:value="status" allow-clear placeholder="全部状态" style="width: 150px" @change="load">
          <Select.Option v-for="item in inquiryStatuses" :key="item" :value="item">{{ item }}</Select.Option>
        </Select>
        <Button @click="load">刷新</Button>
        <span class="text-gray-500">共 {{ inquiries.length }} 条询盘</span>
      </Space>
      <Spin :spinning="loading">
        <Table :columns="columns" :data-source="inquiries" :pagination="{ pageSize: 15 }" :row-key="(row: any) => row.id" :scroll="{ x: 1100 }">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'name'">
              <strong>{{ record.name || '未填写' }}</strong>
            </template>
            <template v-else-if="column.key === 'vehicle_interest'">
              {{ record.vehicle_interest || record.message || '-' }}
            </template>
            <template v-else-if="column.key === 'status'">
              <Tag :color="statusColor(record.status)">{{ record.status || '新询盘' }}</Tag>
            </template>
            <template v-else-if="column.key === 'action'">
              <Space>
                <Select :value="record.status || '新询盘'" size="small" style="width: 120px" @change="(value: any) => changeStatus(record, String(value || ''))">
                  <Select.Option v-for="item in inquiryStatuses" :key="item" :value="item">{{ item }}</Select.Option>
                </Select>
                <Popconfirm title="永久删除这条询盘及其联系方式和需求内容？此操作无法撤销。" @confirm="remove(record)">
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
