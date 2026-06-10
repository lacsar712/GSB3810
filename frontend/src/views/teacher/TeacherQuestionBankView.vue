<template>
  <div class="page-space">
    <header class="head-block">
      <h2 class="page-title">题库资源搜索</h2>
      <p class="page-subtitle">按关键词、科目、年级检索总管理员发布的教学资源。</p>
    </header>

    <div class="card-shell padded-card">
      <div class="toolbar">
        <el-input v-model="filters.keyword" class="custom-input" clearable placeholder="输入标题关键词" style="width: 240px" />
        <el-select v-model="filters.subject" class="custom-select" clearable placeholder="科目" style="width: 140px">
          <el-option v-for="item in subjects" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="filters.grade" class="custom-select" clearable placeholder="年级" style="width: 130px">
          <el-option v-for="item in grades" :key="item" :label="item" :value="item" />
        </el-select>
        <el-button type="primary" @click="loadResources">搜索</el-button>
      </div>

      <el-table :data="resources" v-loading="loading" border>
        <el-table-column prop="title" label="资源标题" min-width="210" />
        <el-table-column prop="subject" label="科目" min-width="90" />
        <el-table-column prop="grade" label="年级" min-width="90" />
        <el-table-column prop="tags" label="标签" min-width="140" />
        <el-table-column prop="description" label="描述" min-width="220" show-overflow-tooltip />
        <el-table-column label="操作" min-width="100">
          <template #default="scope">
            <el-button type="primary" link @click="openResource(scope.row.resource_url)">打开链接</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue';

import http from '../../api/http';

const subjects = ['语文', '数学', '英语', '物理', '化学', '生物'];
const grades = ['高一', '高二', '高三'];

const loading = ref(false);
const resources = ref([]);

const filters = reactive({
  keyword: '',
  subject: '',
  grade: ''
});

const loadResources = async () => {
  loading.value = true;
  try {
    const { data } = await http.get('/teacher/question-bank/search', {
      params: {
        keyword: filters.keyword || undefined,
        subject: filters.subject || undefined,
        grade: filters.grade || undefined
      }
    });
    resources.value = data;
  } finally {
    loading.value = false;
  }
};

const openResource = (url) => {
  window.open(url, '_blank');
};

onMounted(() => {
  loadResources();
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
  margin-bottom: 12px;
}
</style>
