<template>
  <GlobalErrorBoundary>
    <router-view />
  </GlobalErrorBoundary>
</template>

<script setup>
import GlobalErrorBoundary from './components/GlobalErrorBoundary.vue';
</script>
