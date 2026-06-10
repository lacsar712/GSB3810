<template>
  <div class="page-space">
    <header class="head-block">
      <h2 class="page-title">总管理员总览</h2>
      <p class="page-subtitle">查看教师账号、题库资源和系统备份运行状态。</p>
    </header>

    <el-skeleton :loading="loading" animated>
      <template #template>
        <el-row :gutter="16">
          <el-col v-for="n in 4" :key="n" :md="6" :sm="12" :xs="24">
            <div class="card-shell padded-card summary-card">
              <el-skeleton-item variant="h3" style="width: 60%" />
              <el-skeleton-item variant="text" style="width: 30%; margin-top: 14px" />
            </div>
          </el-col>
        </el-row>
      </template>

      <el-row :gutter="16">
        <el-col :md="6" :sm="12" :xs="24">
          <div class="card-shell padded-card summary-card">
            <p class="label">教师账号</p>
            <h3>{{ summary.teacherCount }}</h3>
          </div>
        </el-col>
        <el-col :md="6" :sm="12" :xs="24">
          <div class="card-shell padded-card summary-card">
            <p class="label">启用中账号</p>
            <h3>{{ summary.activeTeacherCount }}</h3>
          </div>
        </el-col>
        <el-col :md="6" :sm="12" :xs="24">
          <div class="card-shell padded-card summary-card">
            <p class="label">题库资源总数</p>
            <h3>{{ summary.resourceCount }}</h3>
          </div>
        </el-col>
        <el-col :md="6" :sm="12" :xs="24">
          <div class="card-shell padded-card summary-card">
            <p class="label">备份记录数</p>
            <h3>{{ summary.backupCount }}</h3>
          </div>
        </el-col>
      </el-row>

      <div class="card-shell padded-card" style="margin-top: 16px">
        <h3 class="section-title">最近一次备份</h3>
        <p class="page-subtitle">{{ summary.latestBackupText }}</p>
      </div>
    </el-skeleton>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue';

import http from '../../api/http';

const loading = ref(false);
const summary = reactive({
  teacherCount: 0,
  activeTeacherCount: 0,
  resourceCount: 0,
  backupCount: 0,
  latestBackupText: '暂无备份记录'
});

const loadData = async () => {
  loading.value = true;
  try {
    const [teacherRes, resourceRes, backupRes] = await Promise.all([
      http.get('/admin/teachers'),
      http.get('/admin/question-resources'),
      http.get('/admin/backups')
    ]);

    const teachers = teacherRes.data || [];
    const resources = resourceRes.data || [];
    const backups = backupRes.data || [];

    summary.teacherCount = teachers.length;
    summary.activeTeacherCount = teachers.filter((item) => item.is_active).length;
    summary.resourceCount = resources.length;
    summary.backupCount = backups.length;

    if (backups[0]) {
      summary.latestBackupText = `${backups[0].file_name}（${new Date(backups[0].created_at).toLocaleString()}）`;
    }
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  loadData();
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
  min-height: 138px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.label {
  margin: 0;
  color: #7c808f;
  letter-spacing: 0.04em;
}

.summary-card h3 {
  margin: 10px 0 0;
  font-size: 34px;
  color: #a1331f;
}

.section-title {
  margin: 0 0 6px;
  font-size: 18px;
}
</style>
