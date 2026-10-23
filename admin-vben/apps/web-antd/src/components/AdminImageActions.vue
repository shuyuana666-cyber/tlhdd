<script lang="ts" setup>
import { ref } from 'vue';

import { Button, Popconfirm } from 'ant-design-vue';

defineProps<{
  imageUrl?: string;
  defaultUrl?: string;
  loading?: boolean;
}>();

const emit = defineEmits<{
  clear: [];
  replace: [file: File];
  restore: [];
}>();

const fileInput = ref<HTMLInputElement>();

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (file) emit('replace', file);
}
</script>

<template>
  <div class="flex min-w-[190px] flex-col gap-2">
    <div class="flex h-14 w-24 items-center justify-center overflow-hidden rounded border border-gray-200 bg-gray-50 text-xs text-gray-400">
      <img v-if="imageUrl" :src="imageUrl" alt="当前页面图片" class="h-full w-full object-cover" />
      <span v-else>无图片</span>
    </div>
    <input
      ref="fileInput"
      accept="image/jpeg,image/png,image/webp"
      class="hidden"
      type="file"
      @change="handleFileChange"
    />
    <div class="flex flex-wrap items-center gap-1">
      <Button html-type="button" size="small" :loading="loading" @click="fileInput?.click()">
        替换图片
      </Button>
      <Popconfirm
        v-if="imageUrl"
        title="清除这张图片？页面对应位置将不再显示图片。"
        @confirm="emit('clear')"
      >
        <Button danger html-type="button" size="small" :disabled="loading">删除图片</Button>
      </Popconfirm>
      <Button
        v-if="defaultUrl && imageUrl !== defaultUrl"
        html-type="button"
        size="small"
        :disabled="loading"
        @click="emit('restore')"
      >
        还原默认
      </Button>
    </div>
  </div>
</template>
