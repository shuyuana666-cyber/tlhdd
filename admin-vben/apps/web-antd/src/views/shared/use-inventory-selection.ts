import { computed, ref } from 'vue';

import { message, Modal } from 'ant-design-vue';

import { bulkDeleteInventory } from '#/api';

export function useInventorySelection(
  resource: 'parts' | 'vehicles',
  label: string,
  reload: () => Promise<void>,
) {
  const selecting = ref(false);
  const deleting = ref(false);
  const selectedIds = ref<number[]>([]);
  const rowSelection = computed(() => selecting.value ? {
    selectedRowKeys: selectedIds.value,
    onChange: (keys: (number | string)[]) => {
      selectedIds.value = keys.map(Number);
    },
    getCheckboxProps: () => ({ disabled: deleting.value }),
    columnWidth: 48,
  } : undefined);

  function clearSelection() {
    selectedIds.value = [];
  }

  function cancelSelection() {
    selecting.value = false;
    clearSelection();
  }

  function confirmDelete() {
    const ids = [...selectedIds.value];
    if (!ids.length || deleting.value) return;
    Modal.confirm({
      title: `永久删除选中的 ${ids.length} 条${label}？`,
      content: '删除后无法撤销，请确认已选中的记录。',
      okText: '确认删除',
      okType: 'danger',
      cancelText: '取消',
      async onOk() {
        deleting.value = true;
        try {
          const result = await bulkDeleteInventory(resource, ids);
          message.success(`已删除 ${result.deleted_count} 条${label}`);
          cancelSelection();
          await reload();
        } finally {
          deleting.value = false;
        }
      },
    });
  }

  return { cancelSelection, clearSelection, confirmDelete, deleting, rowSelection, selectedIds, selecting };
}
