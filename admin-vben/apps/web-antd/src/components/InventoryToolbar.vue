<script lang="ts" setup>
import { ConfigProvider, Typography } from 'ant-design-vue';

defineProps<{
  hint?: string;
  label: string;
}>();

const controlTheme = { token: { borderRadius: 6, controlHeight: 36 } };
</script>

<template>
  <ConfigProvider :theme="controlTheme">
    <div class="inventory-toolbar" role="group" :aria-label="label">
      <div
        class="inventory-toolbar-scroll"
        role="region"
        aria-label="筛选与操作，可横向滚动"
        tabindex="0"
      >
        <div class="inventory-toolbar-row">
          <div class="inventory-toolbar-filters"><slot name="filters"></slot></div>
          <div class="inventory-toolbar-actions"><slot name="actions"></slot></div>
          <Typography.Text class="inventory-toolbar-summary" type="secondary">
            <slot name="summary"></slot>
          </Typography.Text>
        </div>
      </div>
      <Typography.Text v-if="hint" class="inventory-toolbar-hint" type="secondary">
        {{ hint }}
      </Typography.Text>
    </div>
  </ConfigProvider>
</template>

<style scoped>
.inventory-toolbar {
  min-width: 0;
  margin-bottom: 12px;
}

.inventory-toolbar-scroll {
  max-width: 100%;
  padding: 2px;
  margin: -2px;
  overflow-x: auto;
  overscroll-behavior-x: contain;
  scrollbar-width: thin;
}

.inventory-toolbar-row,
.inventory-toolbar-filters,
.inventory-toolbar-actions {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
}

.inventory-toolbar-row {
  gap: 12px;
  min-width: max-content;
  min-height: 36px;
}

.inventory-toolbar-filters {
  gap: 12px;
}

.inventory-toolbar-actions {
  flex-shrink: 0;
  gap: 8px;
}

.inventory-toolbar-summary {
  flex-shrink: 0;
  margin-left: 4px;
  font-size: 13px;
  white-space: nowrap;
}

.inventory-toolbar-hint {
  display: block;
  margin-top: 8px;
  font-size: 12px;
}

.inventory-toolbar-filters :deep(.ant-input-search) {
  flex: 0 0 clamp(220px, 22vw, 320px);
  width: clamp(220px, 22vw, 320px);
}

.inventory-toolbar-filters :deep(.ant-select) {
  flex: 0 0 144px;
  width: 144px;
}

.inventory-toolbar-actions :deep(.ant-btn) {
  white-space: nowrap;
}
</style>
