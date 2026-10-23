<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';

import { Button, Card, Empty, Input, Popconfirm, Space, Spin, Table, Tag, message } from 'ant-design-vue';

import { deleteAdminResource, getAdminSnapshot } from '#/api';

const loading = ref(false);
const search = ref('');
const users = ref<Record<string, any>[]>([]);

const filteredUsers = computed(() => {
  const term = search.value.trim().toLowerCase();
  if (!term) return users.value;
  return users.value.filter((user) =>
    [user.account, user.display_name, user.email, user.phone, user.company, user.role]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
      .includes(term),
  );
});

const columns = [
  { dataIndex: 'display_name', key: 'display_name', title: '姓名' },
  { dataIndex: 'account', key: 'account', title: '账号' },
  { dataIndex: 'company', key: 'company', title: '公司' },
  { dataIndex: 'email', key: 'email', title: '邮箱' },
  { dataIndex: 'phone', key: 'phone', title: '电话' },
  { dataIndex: 'role', key: 'role', title: '角色' },
  { dataIndex: 'created_at', key: 'created_at', title: '注册时间' },
  { dataIndex: 'last_login_at', key: 'last_login_at', title: '最近登录' },
  { key: 'action', title: '操作' },
];

async function load() {
  loading.value = true;
  try {
    const result = await getAdminSnapshot();
    users.value = result.public_users || [];
  } catch (error: any) {
    message.error(error?.message || '用户加载失败');
  } finally {
    loading.value = false;
  }
}

async function remove(user: Record<string, any>) {
  try {
    await deleteAdminResource('users', Number(user.id));
    users.value = users.value.filter((item) => Number(item.id) !== Number(user.id));
    message.success('用户及其关联询盘、会话、论坛帖子和登录会话已永久删除');
  } catch (error: any) {
    message.error(error?.message || '用户删除失败');
  }
}

onMounted(load);
</script>

<template>
  <Page description="管理网站注册用户账号及其关联数据" title="注册用户">
    <Card>
      <Space class="mb-4" wrap>
        <Input.Search v-model:value="search" allow-clear placeholder="搜索姓名、账号、公司或角色" style="width: 320px" />
        <span class="text-gray-500">共 {{ filteredUsers.length }} 个账号</span>
        <Button @click="load">刷新</Button>
      </Space>
      <Spin :spinning="loading">
        <Table :columns="columns" :data-source="filteredUsers" :pagination="{ pageSize: 15 }" :row-key="(row: any) => row.id" :scroll="{ x: 1300 }">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'display_name'">
              <strong>{{ record.display_name || '未填写' }}</strong>
            </template>
            <template v-else-if="column.key === 'role'">
              <Tag color="blue">{{ record.role || '普通用户' }}</Tag>
            </template>
            <template v-else-if="column.key === 'action'">
              <Popconfirm
                :title="`永久删除用户“${record.account}”及其关联询盘、消息会话、论坛帖子和登录会话？此操作无法撤销。`"
                @confirm="remove(record)"
              >
                <Button danger size="small" type="link">删除用户</Button>
              </Popconfirm>
            </template>
          </template>
        </Table>
        <Empty v-if="!filteredUsers.length" description="暂无注册账号" />
      </Spin>
    </Card>
  </Page>
</template>
