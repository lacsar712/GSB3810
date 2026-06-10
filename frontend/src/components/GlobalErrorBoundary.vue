<template>
  <slot />
</template>

<script setup>
import { onErrorCaptured } from 'vue';
import { ElMessage } from 'element-plus';

onErrorCaptured(() => {
  ElMessage.error('页面发生异常，请稍后重试');
  return false;
});
</script>
