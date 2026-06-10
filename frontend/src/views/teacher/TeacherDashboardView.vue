<template>
  <div class="page-space">
    <header class="head-block">
      <h2 class="page-title">教学运营总览</h2>
      <p class="page-subtitle">掌握班级、学生规模和科目平均分整体情况。</p>
    </header>

    <el-row :gutter="16">
      <el-col :md="8" :xs="24">
        <div class="card-shell padded-card summary-card">
          <p class="label">班级数量</p>
          <h3>{{ summary.classCount }}</h3>
        </div>
      </el-col>
      <el-col :md="8" :xs="24">
        <div class="card-shell padded-card summary-card">
          <p class="label">学生人数</p>
          <h3>{{ summary.studentCount }}</h3>
        </div>
      </el-col>
      <el-col :md="8" :xs="24">
        <div class="card-shell padded-card summary-card">
          <p class="label">统计科目</p>
          <h3>{{ summary.subjectCount }}</h3>
        </div>
      </el-col>
    </el-row>

    <div class="card-shell padded-card">
      <div class="chart-head">
        <h3>班级平均分雷达与柱状分析</h3>
        <el-select v-model="selectedClassId" class="custom-select" placeholder="班级筛选" clearable style="width: 180px" @change="loadAverage">
          <el-option v-for="item in classOptions" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
      </div>
      <el-row :gutter="12">
        <el-col :md="12" :xs="24">
          <ChartPanel :option="barOption" :height="340" />
        </el-col>
        <el-col :md="12" :xs="24">
          <ChartPanel :option="radarOption" :height="340" />
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';

import http from '../../api/http';
import ChartPanel from '../../components/ChartPanel.vue';

const classOptions = ref([]);
const selectedClassId = ref();
const averageRows = ref([]);

const summary = ref({
  classCount: 0,
  studentCount: 0,
  subjectCount: 0
});

const barOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 30, right: 20, top: 24, bottom: 26, containLabel: true },
  xAxis: {
    type: 'category',
    data: averageRows.value.map((item) => item.subject),
    axisLabel: { color: '#596173' }
  },
  yAxis: {
    type: 'value',
    min: 0,
    max: 100,
    axisLabel: { color: '#596173' }
  },
  series: [
    {
      type: 'bar',
      data: averageRows.value.map((item) => item.average_score),
      itemStyle: {
        borderRadius: [8, 8, 0, 0],
        color: '#cf4a32'
      }
    }
  ]
}));

const radarOption = computed(() => ({
  tooltip: {},
  radar: {
    indicator: averageRows.value.map((item) => ({ name: item.subject, max: 100 })),
    radius: 100,
    splitArea: { areaStyle: { color: ['#fff6ef', '#ffffff'] } }
  },
  series: [
    {
      type: 'radar',
      data: [
        {
          value: averageRows.value.map((item) => item.average_score),
          name: '平均分',
          areaStyle: { color: 'rgba(207, 74, 50, 0.24)' },
          lineStyle: { color: '#cf4a32' }
        }
      ]
    }
  ]
}));

const loadBase = async () => {
  const [classRes, studentRes] = await Promise.all([http.get('/teacher/classes'), http.get('/teacher/students')]);
  classOptions.value = classRes.data;
  summary.value.classCount = classRes.data.length;
  summary.value.studentCount = studentRes.data.length;
};

const loadAverage = async () => {
  const { data } = await http.get('/teacher/analytics/class-average', {
    params: {
      class_id: selectedClassId.value || undefined
    }
  });
  averageRows.value = data;
  summary.value.subjectCount = data.length;
};

onMounted(async () => {
  await loadBase();
  await loadAverage();
});
</script>

<style scoped>
.page-space {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.head-block {
  padding: 6px 4px;
}

.summary-card {
  min-height: 130px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.label {
  margin: 0;
  color: #71798a;
}

.summary-card h3 {
  margin: 10px 0 0;
  font-size: 34px;
  color: #a1331f;
}

.chart-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.chart-head h3 {
  margin: 0;
  font-size: 18px;
}
</style>
