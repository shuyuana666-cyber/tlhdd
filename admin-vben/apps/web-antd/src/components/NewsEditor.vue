<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue';

import { Button, message } from 'ant-design-vue';

import { uploadAdminMedia } from '#/api';

const props = defineProps<{
  modelValue: string;
  label: string;
  disabled?: boolean;
}>();
const emit = defineEmits<{
  'update:modelValue': [value: string];
  uploading: [value: boolean];
}>();
const editor = ref<HTMLDivElement>();
const fileInput = ref<HTMLInputElement>();
const uploading = ref(false);
let savedRange: Range | undefined;

function update() {
  emit('update:modelValue', editor.value?.innerHTML || '');
}
function command(name: string, value?: string) {
  editor.value?.focus();
  document.execCommand(name, false, value);
  update();
}
function rememberSelection() {
  const selection = window.getSelection();
  savedRange =
    selection?.rangeCount && editor.value?.contains(selection.anchorNode)
      ? selection.getRangeAt(0).cloneRange()
      : undefined;
  fileInput.value?.click();
}
async function insertImage(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (!file) return;
  if (!file.type.startsWith('image/') || file.size > 20 * 1024 * 1024) {
    message.error('请选择不超过 20MB 的图片');
    return;
  }
  uploading.value = true;
  emit('uploading', true);
  try {
    const result = await uploadAdminMedia(file);
    // Restore editability before execCommand inserts at the saved caret.
    uploading.value = false;
    emit('uploading', false);
    await nextTick();
    editor.value?.focus();
    if (savedRange) {
      const selection = window.getSelection();
      selection?.removeAllRanges();
      selection?.addRange(savedRange);
    }
    const url = (result.optimized_url || result.url)
      .replaceAll('&', '&amp;')
      .replaceAll('"', '&quot;')
      .replaceAll('<', '&lt;');
    command('insertHTML', `<p><img src="${url}" alt=""></p><p><br></p>`);
  } catch (error: any) {
    message.error(error?.message || '图片上传失败，请重试');
  } finally {
    uploading.value = false;
    emit('uploading', false);
  }
}
function paste(event: ClipboardEvent) {
  // Paste plain text so external inline styles and event handlers cannot enter the editor.
  command('insertText', event.clipboardData?.getData('text/plain') || '');
}
function sync() {
  if (editor.value && editor.value.innerHTML !== props.modelValue)
    editor.value.innerHTML = props.modelValue || '';
}
watch(() => props.modelValue, sync);
onMounted(sync);
</script>

<template>
  <div class="news-editor">
    <div class="news-editor-tools" role="toolbar" aria-label="正文格式">
      <Button
        size="small"
        :disabled="disabled || uploading"
        @mousedown.prevent
        @click="command('formatBlock', 'p')"
        >
正文
</Button>
      <Button
        size="small"
        :disabled="disabled || uploading"
        @mousedown.prevent
        @click="command('formatBlock', 'h2')"
        >
小标题
</Button>
      <Button
        size="small"
        :disabled="disabled || uploading"
        @mousedown.prevent
        @click="command('bold')"
        >
<strong>加粗</strong>
</Button>
      <Button
        size="small"
        :disabled="disabled || uploading"
        @mousedown.prevent
        @click="command('insertUnorderedList')"
        >
列表
</Button>
      <Button
        size="small"
        :disabled="disabled || uploading"
        :loading="uploading"
        @mousedown.prevent
        @click="rememberSelection"
        >
插入图片
</Button>
      <Button
        size="small"
        :disabled="disabled || uploading"
        @mousedown.prevent
        @click="command('undo')"
        >
撤销
</Button>
    </div>
    <div
      ref="editor"
      class="news-editor-content"
      :contenteditable="!disabled && !uploading"
      role="textbox"
      aria-multiline="true"
      :aria-label="label"
      data-placeholder="输入正文，可插入小标题、列表与图片"
      @input="update"
      @paste.prevent="paste"
    ></div>
    <input
      ref="fileInput"
      type="file"
      accept="image/*"
      hidden
      @change="insertImage"
    />
  </div>
</template>

<style scoped>
.news-editor {
  border: 1px solid var(--ant-color-border, #d9d9d9);
  border-radius: 6px;
  overflow: hidden;
}
.news-editor:focus-within {
  border-color: var(--ant-color-primary, #1677ff);
}
.news-editor-tools {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--ant-color-border, #d9d9d9);
}
.news-editor-content {
  min-height: 320px;
  max-height: 55vh;
  overflow-y: auto;
  padding: 20px;
  outline: none;
  font-size: 14px;
  line-height: 28px;
  overflow-wrap: anywhere;
}
.news-editor-content:empty::before {
  content: attr(data-placeholder);
  color: #999;
  pointer-events: none;
}
.news-editor-content :deep(p) {
  margin: 0;
}
.news-editor-content :deep(h2) {
  margin: 12px 0 4px;
  font-size: 20px;
  font-weight: 700;
}
.news-editor-content :deep(img) {
  max-width: 100%;
  height: auto;
}
.news-editor-content :deep(ul),
.news-editor-content :deep(ol) {
  padding-left: 24px;
}
</style>
