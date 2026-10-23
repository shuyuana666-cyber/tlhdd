<script lang="ts" setup>
import { onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  Button,
  Card,
  Col,
  Divider,
  Form,
  Input,
  Row,
  Space,
  Spin,
  message,
} from 'ant-design-vue';

import {
  changeAdminPassword,
  getAdminSnapshot,
  saveAdminSettings,
} from '#/api';

const loading = ref(false);
const saving = ref(false);
const passwordSaving = ref(false);
const settings = reactive<Record<string, any>>({});
const password = reactive({ old_password: '', new_password: '' });

const settingFields = [
  { key: 'company_name', label: '公司名称' },
  { key: 'service_hours', label: '服务时间' },
  { key: 'phone', label: '电话' },
  { key: 'email', label: '邮箱' },
  { key: 'whatsapp', label: 'WhatsApp' },
  { key: 'wechat', label: '微信' },
  { key: 'address', label: '地址', full: true },
  { key: 'footer_note', label: '页脚简介', full: true, textarea: true },
  { key: 'seo_title', label: 'SEO 标题', full: true },
  { key: 'seo_description', label: 'SEO 描述', full: true, textarea: true },
  { key: 'site_notice', label: '站点公告 / 顶部提示', full: true, textarea: true },
  { key: 'used_catalog_title', label: '二手车列表标题', full: true },
  { key: 'used_catalog_intro', label: '二手车列表说明', full: true, textarea: true },
  { key: 'used_detail_description_title', label: '详情页描述标题', full: true },
  { key: 'used_detail_fallback_description', label: '详情页默认描述', full: true, textarea: true },
  { key: 'custom_css', label: '自定义样式', full: true, textarea: true },
];

async function load() {
  loading.value = true;
  try {
    const result = await getAdminSnapshot();
    Object.assign(settings, result.settings || {});
  } catch (error: any) {
    message.error(error?.message || '设置加载失败');
  } finally {
    loading.value = false;
  }
}

async function save() {
  saving.value = true;
  try {
    const result = await saveAdminSettings({ ...settings });
    Object.assign(settings, result.settings || settings);
    message.success('系统设置已保存');
  } catch (error: any) {
    message.error(error?.message || '设置保存失败');
  } finally {
    saving.value = false;
  }
}

async function updatePassword() {
  if (password.new_password.length < 12) {
    message.warning('新密码至少需要 12 位');
    return;
  }
  passwordSaving.value = true;
  try {
    await changeAdminPassword({ ...password });
    password.old_password = '';
    password.new_password = '';
    message.success('密码已更新，请使用新密码登录');
  } catch (error: any) {
    message.error(error?.message || '密码修改失败');
  } finally {
    passwordSaving.value = false;
  }
}

async function downloadBackup() {
  try {
    const response = await fetch('/api/admin/backup', { credentials: 'same-origin' });
    if (!response.ok) throw new Error('备份下载失败');
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `tlhdd-mysql-${new Date().toISOString().slice(0, 19).replaceAll(':', '')}.sql`;
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    message.success('数据库备份已开始下载');
  } catch (error: any) {
    message.error(error?.message || '备份下载失败');
  }
}

onMounted(load);
</script>

<template>
  <Page description="维护企业资料、SEO 文案和管理员账号" title="系统设置">
    <Spin :spinning="loading">
      <Row :gutter="16">
        <Col :span="16" :xs="24" :lg="16">
          <Card title="企业资料与全站内容">
            <Form layout="vertical">
              <Row :gutter="16">
                <Col
                  v-for="field in settingFields"
                  :key="field.key"
                  :span="field.full ? 24 : 12"
                  :xs="24"
                  :sm="field.full ? 24 : 12"
                >
                  <Form.Item :label="field.label">
                    <Input.TextArea
                      v-if="field.textarea"
                      v-model:value="settings[field.key]"
                      :auto-size="{ minRows: 3, maxRows: 8 }"
                    />
                    <Input v-else v-model:value="settings[field.key]" />
                  </Form.Item>
                </Col>
              </Row>
              <Space>
                <Button :loading="saving" type="primary" @click="save">保存设置</Button>
                <Button @click="load">重新加载</Button>
                <Button @click="downloadBackup">下载数据备份</Button>
              </Space>
            </Form>
          </Card>
        </Col>
        <Col :span="8" :xs="24" :lg="8">
          <Card title="修改管理员密码">
            <Form layout="vertical">
              <Form.Item label="旧密码">
                <Input.Password v-model:value="password.old_password" autocomplete="current-password" />
              </Form.Item>
              <Form.Item label="新密码">
                <Input.Password v-model:value="password.new_password" autocomplete="new-password" />
              </Form.Item>
              <Button :loading="passwordSaving" type="primary" @click="updatePassword">更新密码</Button>
            </Form>
            <Divider />
            <p class="text-gray-500">建议使用 12 位以上的随机密码，并妥善保存数据库备份。</p>
          </Card>
        </Col>
      </Row>
    </Spin>
  </Page>
</template>
