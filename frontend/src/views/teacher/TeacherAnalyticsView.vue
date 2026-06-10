<template>
  <div class="page-space">
    <header class="head-block">
      <h2 class="page-title">成绩分析与可视化</h2>
      <p class="page-subtitle">支持班级均分、个人趋势、科目平衡，提供导出与打印报告能力。</p>
    </header>

    <div class="card-shell padded-card">
      <div class="toolbar">
        <el-select v-model="filters.class_id" class="custom-select" clearable placeholder="班级筛选" style="width: 170px">
          <el-option v-for="item in classes" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-select v-model="filters.student_id" class="custom-select" placeholder="学生筛选" style="width: 220px">
          <el-option
            v-for="item in students"
            :key="item.id"
            :label="`${item.full_name}(${item.student_no})`"
            :value="item.id"
          />
        </el-select>
        <el-select v-model="filters.subject" class="custom-select" placeholder="科目筛选" style="width: 140px">
          <el-option v-for="item in subjects" :key="item" :label="item" :value="item" />
        </el-select>
        <el-button type="primary" @click="refreshAnalytics">更新分析</el-button>
        <el-button @click="exportCsv">导出 CSV</el-button>
        <el-button type="warning" @click="preparePrint">打印报告</el-button>
      </div>

      <el-row :gutter="12">
        <el-col :lg="12" :xs="24">
          <div class="mini-card">
            <h4>班级科目平均分</h4>
            <ChartPanel :option="classAverageOption" :height="300" />
          </div>
        </el-col>
        <el-col :lg="12" :xs="24">
          <div class="mini-card">
            <h4>个人成绩趋势（折线）</h4>
            <ChartPanel :option="trendOption" :height="300" />
          </div>
        </el-col>
      </el-row>

      <el-row :gutter="12" style="margin-top: 12px">
        <el-col :span="24">
          <div class="mini-card">
            <h4>个人各科均衡性（雷达图）</h4>
            <ChartPanel :option="radarOption" :height="320" />
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';

import http from '../../api/http';
import ChartPanel from '../../components/ChartPanel.vue';

const subjects = ['语文', '数学', '英语', '物理', '化学', '生物'];

const classes = ref([]);
const students = ref([]);

const classAverage = ref([]);
const trendRows = ref([]);
const balanceRows = ref([]);

const filters = reactive({
  class_id: null,
  student_id: null,
  subject: '数学'
});

const classAverageOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 30, right: 20, top: 24, bottom: 24, containLabel: true },
  xAxis: { type: 'category', data: classAverage.value.map((item) => item.subject) },
  yAxis: { type: 'value', min: 0, max: 100 },
  series: [
    {
      type: 'bar',
      data: classAverage.value.map((item) => item.average_score),
      itemStyle: { color: '#cf4a32', borderRadius: [8, 8, 0, 0] }
    }
  ]
}));

const trendOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['成绩', '排名'] },
  xAxis: { type: 'category', data: trendRows.value.map((item) => item.exam_name) },
  yAxis: [
    { type: 'value', min: 0, max: 100, name: '成绩' },
    { type: 'value', inverse: true, min: 1, name: '排名' }
  ],
  series: [
    {
      name: '成绩',
      type: 'line',
      smooth: true,
      data: trendRows.value.map((item) => item.score),
      lineStyle: { color: '#cf4a32' },
      itemStyle: { color: '#cf4a32' }
    },
    {
      name: '排名',
      type: 'line',
      yAxisIndex: 1,
      smooth: true,
      data: trendRows.value.map((item) => item.rank || null),
      lineStyle: { color: '#5f73c7' },
      itemStyle: { color: '#5f73c7' }
    }
  ]
}));

const radarOption = computed(() => ({
  tooltip: {},
  radar: {
    indicator: balanceRows.value.map((item) => ({ name: item.subject, max: 100 })),
    radius: 110,
    splitArea: { areaStyle: { color: ['#fff6ef', '#fff'] } }
  },
  series: [
    {
      type: 'radar',
      data: [
        {
          value: balanceRows.value.map((item) => item.score),
          name: '最新成绩',
          areaStyle: { color: 'rgba(95, 115, 199, 0.25)' },
          lineStyle: { color: '#5f73c7' }
        }
      ]
    }
  ]
}));

const loadBase = async () => {
  const [classRes, studentRes] = await Promise.all([http.get('/teacher/classes'), http.get('/teacher/students')]);
  classes.value = classRes.data;
  students.value = studentRes.data;
  if (!filters.student_id && studentRes.data[0]) {
    filters.student_id = studentRes.data[0].id;
  }
};

const loadClassAverage = async () => {
  const { data } = await http.get('/teacher/analytics/class-average', {
    params: {
      class_id: filters.class_id || undefined,
      subject: filters.subject || undefined
    }
  });
  classAverage.value = data;
};

const loadTrend = async () => {
  if (!filters.student_id) return;
  const { data } = await http.get('/teacher/analytics/ranking-trend', {
    params: {
      student_id: filters.student_id,
      subject: filters.subject || undefined
    }
  });
  trendRows.value = data;
};

const loadBalance = async () => {
  if (!filters.student_id) return;
  const { data } = await http.get('/teacher/analytics/subject-balance', {
    params: {
      student_id: filters.student_id
    }
  });
  balanceRows.value = data;
};

const refreshAnalytics = async () => {
  if (!filters.student_id) {
    ElMessage.warning('请先选择学生');
    return;
  }
  await Promise.all([loadClassAverage(), loadTrend(), loadBalance()]);
};

const exportCsv = async () => {
  const response = await http.get('/teacher/analytics/export', {
    params: {
      class_id: filters.class_id || undefined,
      subject: filters.subject || undefined
    },
    responseType: 'blob'
  });

  const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'scores_export.csv';
  link.click();
  window.URL.revokeObjectURL(url);
};

const preparePrint = async () => {
  if (!filters.student_id) {
    ElMessage.warning('请先选择学生');
    return;
  }

  const { data } = await http.get('/teacher/analytics/print-report', {
    params: { student_id: filters.student_id }
  });

  const win = window.open('', '_blank');
  if (!win) {
    ElMessage.warning('请允许浏览器弹出窗口后重试');
    return;
  }

  const rows = data.scores
    .map(
      (item) =>
        `<tr><td>${item.exam_name}</td><td>${item.subject}</td><td>${item.exam_date}</td><td>${item.score}</td><td>${item.rank ?? '-'}</td></tr>`
    )
    .join('');
  const behaviorRows = data.behaviors
    .map(
      (item) => `<tr><td>${item.record_date}</td><td>${item.category}</td><td>${item.title}</td><td>${item.score_delta}</td></tr>`
    )
    .join('');

  win.document.write(`
    <html>
      <head>
        <title>学生分析报告</title>
        <style>
          body { font-family: 'PingFang SC', sans-serif; padding: 24px; }
          h1 { margin: 0 0 10px; }
          table { width: 100%; border-collapse: collapse; margin-top: 10px; }
          th, td { border: 1px solid #ddd; padding: 8px; font-size: 13px; }
          th { background: #f6f6f6; }
        </style>
      </head>
      <body>
        <h1>${data.student.name} 学生分析报告</h1>
        <p>学号：${data.student.student_no} | 班级：${data.student.class_name}</p>
        <h3>成绩概览</h3>
        <table>
          <thead><tr><th>考试</th><th>科目</th><th>日期</th><th>成绩</th><th>排名</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
        <h3>在校表现</h3>
        <table>
          <thead><tr><th>日期</th><th>类别</th><th>标题</th><th>分值变化</th></tr></thead>
          <tbody>${behaviorRows}</tbody>
        </table>
      </body>
    </html>
  `);
  win.document.close();
  win.focus();
  win.print();
};

onMounted(async () => {
  await loadBase();
  await refreshAnalytics();
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

.toolbar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

.mini-card {
  border: 1px solid #e6daca;
  border-radius: 14px;
  padding: 12px;
  min-height: 340px;
  background: linear-gradient(180deg, #fffdf9 0%, #fff 100%);
}

.mini-card h4 {
  margin: 4px 0 12px;
  font-size: 16px;
}
</style>
