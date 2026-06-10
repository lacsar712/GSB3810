<template>
  <div ref="chartRef" class="chart-panel"></div>
</template>

<script setup>
import * as echarts from 'echarts';
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';

const props = defineProps({
  option: {
    type: Object,
    required: true
  },
  height: {
    type: Number,
    default: 320
  }
});

const chartRef = ref(null);
let chartInstance = null;

const renderChart = async () => {
  await nextTick();
  if (!chartRef.value) {
    return;
  }
  chartRef.value.style.height = `${props.height}px`;
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value);
    window.addEventListener('resize', resizeChart);
  }
  chartInstance.setOption(props.option, true);
};

const resizeChart = () => {
  if (chartInstance) {
    chartInstance.resize();
  }
};

watch(
  () => props.option,
  () => {
    renderChart();
  },
  { deep: true }
);

onMounted(() => {
  renderChart();
});

onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.dispose();
    chartInstance = null;
  }
  window.removeEventListener('resize', resizeChart);
});
</script>

<style scoped>
.chart-panel {
  width: 100%;
  min-height: 220px;
}
</style>
