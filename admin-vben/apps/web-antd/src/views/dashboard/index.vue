<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  Alert,
  Button,
  Card,
  Col,
  Empty,
  Row,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  message,
} from 'ant-design-vue';

import { getAdminSummary } from '#/api';

const loading = ref(true);
const summary = ref<Record<string, any>>({});

const cards = computed(() => [
  {
    color: '#1677ff',
    title: '待处理线索',
    value:
      Number(summary.value.new_inquiries || 0) +
      Number(summary.value.open_messages || 0),
  },
  {
    color: '#13c2c2',
    title: '库存总量',
    value: Number(summary.value.total_vehicles || 0),
  },
  {
    color: '#52c41a',
    title: '已上架车辆',
    value: Number(summary.value.active_vehicles || 0),
  },
  {
    color: '#fa8c16',
    title: '已上架配件',
    value: Number(summary.value.active_parts || 0),
  },
]);

const vehicleColumns = [
  { dataIndex: 'title', key: 'title', title: '车辆' },
  { dataIndex: 'vehicle_type', key: 'vehicle_type', title: '类型' },
  { dataIndex: 'brand', key: 'brand', title: '品牌' },
  { dataIndex: 'price', key: 'price', title: '价格' },
  { dataIndex: 'updated_at', key: 'updated_at', title: '更新时间' },
];

function vehicleTypeLabel(value: string) {
  return value === 'used' ? '二手车' : '新车';
}

async function load() {
  loading.value = true;
  try {
    summary.value = await getAdminSummary();
  } catch (error: any) {
    message.error(error?.message || '概览加载失败');
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <Page description="实时查看线索、库存和内容运营状态" title="运营总览">
    <Spin :spinning="loading">
      <Alert
        class="mb-4"
        message="欢迎回到通利华汽车集团后台"
        description="这里汇总客户线索、车辆库存和网站内容的最新状态。"
        show-icon
        type="info"
      />

      <Row :gutter="16" class="mb-4">
        <Col v-for="card in cards" :key="card.title" :span="6" :xs="24" :sm="12" :lg="6">
          <Card :body-style="{ padding: '20px' }" class="h-full">
            <Statistic :value="card.value" :value-style="{ color: card.color }" :title="card.title" />
          </Card>
        </Col>
      </Row>

      <Row :gutter="16">
        <Col :span="16" :xs="24" :lg="16">
          <Card title="最近更新车辆">
            <template #extra>
              <Space>
                <Tag color="blue">推荐 {{ summary.featured_vehicles || 0 }}</Tag>
                <Tag color="orange">缺图 {{ summary.missing_vehicle_images || 0 }}</Tag>
              </Space>
            </template>
            <Table
              :columns="vehicleColumns"
              :data-source="summary.recent_vehicles || []"
              :pagination="false"
              :row-key="(row: any) => row.id"
              size="small"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'vehicle_type'">
                  <Tag :color="record.vehicle_type === 'used' ? 'gold' : 'green'">
                    {{ vehicleTypeLabel(record.vehicle_type) }}
                  </Tag>
                </template>
                <template v-else-if="column.key === 'title'">
                  <strong>{{ record.title || '未命名车辆' }}</strong>
                </template>
              </template>
            </Table>
            <Empty v-if="!(summary.recent_vehicles || []).length" description="暂无车辆更新" />
          </Card>
        </Col>
        <Col :span="8" :xs="24" :lg="8">
          <Card class="h-full" title="库存健康度">
            <div class="space-y-4">
              <div class="flex items-center justify-between">
                <span>停用车辆</span><Tag color="default">{{ summary.inactive_vehicles || 0 }}</Tag>
              </div>
              <div class="flex items-center justify-between">
                <span>推荐车辆</span><Tag color="green">{{ summary.featured_vehicles || 0 }}</Tag>
              </div>
              <div class="flex items-center justify-between">
                <span>首页轮播</span><Tag color="blue">{{ summary.active_slides || 0 }}</Tag>
              </div>
              <div class="flex items-center justify-between">
                <span>待回复消息</span><Tag color="red">{{ summary.open_messages || 0 }}</Tag>
              </div>
            </div>
            <Space class="mt-6" direction="vertical" style="width: 100%">
              <Button block href="#/vehicles" type="primary">管理车辆</Button>
              <Button block href="#/homepage">配置首页</Button>
            </Space>
          </Card>
        </Col>
      </Row>
    </Spin>
  </Page>
</template>
