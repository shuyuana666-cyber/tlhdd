<script lang="ts" setup>
import { computed, onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  Alert,
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  message,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
} from 'ant-design-vue';

import {
  deleteAdminResource,
  getAdminNews,
  saveAdminResource,
  uploadAdminMedia,
} from '#/api';
import NewsEditor from '#/components/NewsEditor.vue';

const rows = ref<Record<string, any>[]>([]);
const loading = ref(false);
const error = ref('');
const query = ref('');
const status = ref('');
const visible = ref(false);
const saving = ref(false);
const uploading = ref(false);
const coverUploading = ref(false);
const removing = ref<number>();
const formError = ref('');
const activeLanguage = ref('zh');
const form = reactive<Record<string, any>>({});
const coverInput = ref<HTMLInputElement>();
let initialForm = '';
const languages = [
  { key: 'zh', tab: '中文（必填）' },
  { key: 'en', tab: 'English（选填）' },
  { key: 'ru', tab: 'Русский（选填）' },
];
const busy = computed(
  () => saving.value || uploading.value || coverUploading.value,
);
const filtered = computed(() =>
  rows.value.filter(
    (row) =>
      (!status.value || row.status === status.value) &&
      `${row.title_zh} ${row.title_en} ${row.title_ru} ${row.source}`
        .toLowerCase()
        .includes(query.value.trim().toLowerCase()),
  ),
);
const columns = [
  { title: '新闻标题', dataIndex: 'title_zh', key: 'title', ellipsis: true },
  { title: '分类', key: 'category', width: 110 },
  { title: '状态', key: 'status', width: 110 },
  { title: '发布时间（北京时间）', key: 'published_at', width: 190 },
  { title: '排序', dataIndex: 'sort_order', width: 80 },
  { title: '操作', key: 'action', width: 190 },
];
function beijing(value: string) {
  if (!value) return '';
  const date = new Date(value.replace(' ', 'T') + 'Z');
  return Number.isNaN(date.getTime())
    ? ''
    : new Date(date.getTime() + 8 * 3600_000).toISOString().slice(0, 16);
}
async function load() {
  loading.value = true;
  error.value = '';
  try {
    rows.value = (await getAdminNews()).news;
  } catch (err: any) {
    error.value = err?.message || '新闻加载失败，请重试';
  } finally {
    loading.value = false;
  }
}
function edit(record?: Record<string, any>) {
  for (const key of Object.keys(form)) delete form[key];
  Object.assign(
    form,
    {
      title_zh: '',
      title_en: '',
      title_ru: '',
      summary_zh: '',
      summary_en: '',
      summary_ru: '',
      content_zh: '',
      content_en: '',
      content_ru: '',
      source: '通利华汽车集团',
      category: 'company',
      status: 'draft',
      published_at: '',
      image_url: '',
      sort_order: 0,
    },
    record || {},
  );
  form.published_at = beijing(record?.published_at || '');
  initialForm = JSON.stringify(form);
  activeLanguage.value = 'zh';
  formError.value = '';
  visible.value = true;
}
function close() {
  if (busy.value) return;
  if (JSON.stringify(form) !== initialForm) {
    Modal.confirm({
      title: '放弃未保存的修改？',
      content: '关闭后，本次编辑的内容不会保存。',
      okText: '放弃修改',
      cancelText: '继续编辑',
      onOk: () => {
        visible.value = false;
      },
    });
  } else visible.value = false;
}
async function save() {
  formError.value = '';
  if (
    !form.title_zh.trim() ||
    !form.content_zh.replace(/<[^>]*>|&nbsp;|\s/g, '')
  ) {
    formError.value = '请填写中文标题和正文';
    activeLanguage.value = 'zh';
    return;
  }
  saving.value = true;
  try {
    await saveAdminResource('news', { ...form }, form.id);
    visible.value = false;
    message.success(
      form.status === 'published'
        ? '新闻已保存，前台按发布时间展示'
        : '草稿已保存',
    );
    await load();
  } catch (err: any) {
    formError.value = err?.message || '保存失败，请重试';
  } finally {
    saving.value = false;
  }
}
async function remove(record: Record<string, any>) {
  removing.value = record.id;
  try {
    await deleteAdminResource('news', record.id);
    message.success('新闻已删除');
    await load();
  } catch (err: any) {
    message.error(err?.message || '删除失败');
  } finally {
    removing.value = undefined;
  }
}
async function uploadCover(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (!file) return;
  if (!file.type.startsWith('image/') || file.size > 20 * 1024 * 1024) {
    message.error('请选择不超过 20MB 的图片');
    return;
  }
  coverUploading.value = true;
  try {
    const result = await uploadAdminMedia(file);
    form.image_url = result.optimized_url || result.url;
  } catch (err: any) {
    message.error(err?.message || '封面上传失败');
  } finally {
    coverUploading.value = false;
  }
}
onMounted(load);
</script>

<template>
  <Page
    title="新闻中心"
    description="管理首页、新闻列表与新闻详情中的内容。草稿不会在前台显示。"
  >
    <Card>
      <div class="news-toolbar">
        <div class="news-filters">
          <Input
            v-model:value="query"
            allow-clear
            placeholder="搜索标题或来源"
            aria-label="搜索新闻"
            class="news-search"
          />
          <Select
            v-model:value="status"
            aria-label="筛选发布状态"
            class="news-status"
            :options="[
              { value: '', label: '全部状态' },
              { value: 'draft', label: '草稿' },
              { value: 'published', label: '已发布 / 定时发布' },
            ]"
          />
          <Button :loading="loading" @click="load">刷新</Button>
        </div>
        <Button type="primary" @click="edit()">新增新闻</Button>
      </div>
      <Alert
        v-if="error"
        type="error"
        :message="error"
        show-icon
        class="news-error"
      />
      <Table
        :columns="columns"
        :data-source="filtered"
        :loading="loading"
        row-key="id"
        :scroll="{ x: 960 }"
        :pagination="{
          pageSize: 10,
          showSizeChanger: true,
          showTotal: (total: number) => `共 ${total} 篇`,
        }"
        :locale="{
          emptyText: error
            ? '加载失败，请点击刷新重试'
            : query || status
              ? '没有匹配的新闻'
              : '暂无新闻，点击「新增新闻」开始创建',
        }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'title'">
<Button
              type="link"
              class="news-title"
              :title="record.title_zh"
              @click="edit(record)"
              >
{{ record.title_zh }}
</Button>
</template>
          <template v-else-if="column.key === 'category'">
{{
            record.category === 'industry' ? '行业动态' : '公司资讯'
          }}
</template>
          <template v-else-if="column.key === 'status'">
<Tag :color="record.status === 'draft' ? 'default' : 'green'">
{{
              record.status === 'draft'
                ? '草稿'
                : record.published_at &&
                    new Date(
                      `${record.published_at.replace(' ', 'T')}Z`,
                    ).getTime() > Date.now()
                  ? '定时发布'
                  : '已发布'
            }}
</Tag>
</template>
          <template v-else-if="column.key === 'published_at'">
{{
            beijing(record.published_at).replace('T', ' ') || '未设置'
          }}
</template>
          <template v-else-if="column.key === 'action'">
            <Space :size="4">
              <Button size="small" type="link" @click="edit(record)">
编辑
</Button>
              <Button
                v-if="
                  record.status === 'published' &&
                  (!record.published_at ||
                    new Date(
                      `${record.published_at.replace(' ', 'T')}Z`,
                    ).getTime() <= Date.now())
                "
                size="small"
                type="link"
                :href="`/news-detail.html?id=${encodeURIComponent(record.slug)}`"
                target="_blank"
                rel="noopener"
                >
查看
</Button>
              <Popconfirm
                title="确定删除这篇新闻？"
                description="删除后，首页、列表和详情页将同步移除。"
                ok-text="删除"
                cancel-text="取消"
                @confirm="remove(record)"
                >
<Button
                  size="small"
                  type="link"
                  danger
                  :loading="removing === record.id"
                  >
删除
</Button>
</Popconfirm>
            </Space>
          </template>
        </template>
      </Table>
    </Card>
    <Modal
      :open="visible"
      :title="form.id ? '编辑新闻' : '新增新闻'"
      :width="1040"
      :mask-closable="false"
      :closable="!busy"
      :keyboard="!busy"
      destroy-on-close
      @cancel="close"
    >
      <Form layout="vertical" class="news-form">
        <Alert
          v-if="formError"
          type="error"
          :message="formError"
          show-icon
          class="news-error"
          role="alert"
        />
        <div class="news-settings">
          <Form.Item label="新闻分类">
<Select
              v-model:value="form.category"
              :disabled="busy"
              :options="[
                { value: 'company', label: '公司资讯' },
                { value: 'industry', label: '行业动态' },
              ]"
          />
</Form.Item>
          <Form.Item label="发布状态">
<Select
              v-model:value="form.status"
              :disabled="busy"
              :options="[
                { value: 'draft', label: '草稿' },
                { value: 'published', label: '发布' },
              ]"
          />
</Form.Item>
          <Form.Item
            label="发布时间（北京时间）"
            help="留空则发布时使用当前时间；未来时间将定时展示。"
            >
<Input
              v-model:value="form.published_at"
              type="datetime-local"
              :disabled="busy"
              aria-label="发布时间（北京时间）"
          />
</Form.Item>
          <Form.Item label="排序" help="数字越小越靠前。">
<InputNumber
              v-model:value="form.sort_order"
              :min="-1000000"
              :max="1000000"
              :precision="0"
              :disabled="busy"
              class="news-order"
          />
</Form.Item>
        </div>
        <Form.Item label="文章来源">
<Input
            v-model:value="form.source"
            :maxlength="200"
            :disabled="busy"
            aria-label="文章来源"
        />
</Form.Item>
        <Form.Item
          label="封面图片"
          help="用于首页预览。正文图片请在编辑器中插入。"
        >
          <div class="news-cover">
            <img
              v-if="form.image_url"
              :src="form.image_url"
              alt="新闻封面预览"
            />
            <Button
              :loading="coverUploading"
              :disabled="busy"
              @click="coverInput?.click()"
              >
{{ form.image_url ? '更换封面' : '上传封面' }}
</Button>
            <Button
              v-if="form.image_url"
              :disabled="busy"
              @click="form.image_url = ''"
              >
移除封面
</Button>
            <input
              ref="coverInput"
              type="file"
              accept="image/*"
              hidden
              @change="uploadCover"
            />
          </div>
        </Form.Item>
        <Tabs v-model:active-key="activeLanguage">
          <Tabs.TabPane
            v-for="lang in languages"
            :key="lang.key"
            :tab="lang.tab"
            :force-render="false"
          >
            <Form.Item
              :label="`${lang.tab.split('（')[0]}标题`"
              :required="lang.key === 'zh'"
              >
<Input
                v-model:value="form[`title_${lang.key}`]"
                :maxlength="300"
                show-count
                :disabled="busy"
                :aria-label="`${lang.key}新闻标题`"
            />
</Form.Item>
            <Form.Item label="摘要（用于首页和列表）">
<Input.TextArea
                v-model:value="form[`summary_${lang.key}`]"
                :maxlength="2000"
                :rows="2"
                show-count
                :disabled="busy"
                :aria-label="`${lang.key}新闻摘要`"
                placeholder="选填，未填写时将自动摘取正文"
            />
</Form.Item>
            <Form.Item label="新闻正文" :required="lang.key === 'zh'">
<NewsEditor
                v-model="form[`content_${lang.key}`]"
                :label="`${lang.key}新闻正文`"
                :disabled="saving || coverUploading"
                @uploading="uploading = $event"
            />
</Form.Item>
          </Tabs.TabPane>
        </Tabs>
        <p class="news-help">
          英文、俄文留空时，前台会显示中文内容。正文统一使用参考页的字体和段落样式。
        </p>
      </Form>
      <template #footer>
<Space>
<Button :disabled="busy" @click="close">取消</Button><Button
            type="primary"
            :loading="saving"
            :disabled="uploading || coverUploading"
            @click="save"
            >
{{
              form.status === 'published' ? '保存并发布' : '保存草稿'
            }}
</Button>
</Space>
</template>
    </Modal>
  </Page>
</template>

<style scoped>
.news-toolbar,
.news-filters,
.news-cover {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.news-toolbar {
  justify-content: space-between;
  margin-bottom: 24px;
}
.news-search {
  width: 260px;
  max-width: 100%;
}
.news-status {
  width: 180px;
}
.news-title {
  max-width: 100%;
  padding: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.news-error {
  margin-bottom: 16px;
}
.news-settings {
  display: grid;
  grid-template-columns: 1fr 1fr 1.5fr 0.65fr;
  gap: 16px;
}
.news-order {
  width: 100%;
}
.news-form {
  padding-top: 16px;
}
.news-cover img {
  width: 120px;
  height: 72px;
  object-fit: cover;
  border-radius: 4px;
}
.news-help {
  color: #888;
  font-size: 12px;
  margin-top: 12px;
}
@media (max-width: 768px) {
  .news-settings {
    grid-template-columns: 1fr 1fr;
  }
  .news-search {
    flex: 1;
    min-width: 160px;
  }
  .news-filters {
    flex: 1;
  }
}
@media (max-width: 480px) {
  .news-settings {
    grid-template-columns: 1fr;
  }
}
</style>
