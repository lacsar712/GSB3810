<template>
  <div class="page-space">
    <header class="head-block">
      <h2 class="page-title">通知与学习资料发布</h2>
      <p class="page-subtitle">支持班级通知、个人消息和学习资料推送。</p>
    </header>

    <el-row :gutter="16">
      <el-col :lg="9" :xs="24">
        <div class="card-shell padded-card">
          <h3 class="section-title">发布新消息</h3>
          <el-form label-position="top">
            <el-form-item label="消息类型">
              <el-select v-model="form.notice_type" class="custom-select" placeholder="请选择消息类型">
                <el-option label="班级通知" value="CLASS" />
                <el-option label="个人消息" value="PERSONAL" />
                <el-option label="公告通知" value="ANNOUNCEMENT" />
                <el-option label="学习资料" value="RESOURCE" />
              </el-select>
            </el-form-item>

            <el-form-item label="班级" v-if="form.notice_type === 'CLASS' || form.notice_type === 'RESOURCE'">
              <el-select v-model="form.class_id" class="custom-select" placeholder="请选择班级">
                <el-option v-for="item in classes" :key="item.id" :label="item.name" :value="item.id" />
              </el-select>
            </el-form-item>

            <el-form-item label="目标学生" v-if="form.notice_type === 'PERSONAL'">
              <el-select v-model="form.target_user_id" class="custom-select" placeholder="请选择目标学生">
                <el-option
                  v-for="student in students"
                  :key="student.user_id"
                  :label="`${student.full_name}(${student.student_no})`"
                  :value="student.user_id"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="标题">
              <el-input v-model="form.title" class="custom-input" maxlength="120" placeholder="请输入标题" />
            </el-form-item>
            <el-form-item label="内容">
              <el-input v-model="form.content" class="custom-input" type="textarea" :rows="4" maxlength="2000" placeholder="请输入内容" />
            </el-form-item>

            <el-button type="primary" :loading="submitting" @click="submitNotice">发布消息</el-button>
          </el-form>
        </div>
      </el-col>

      <el-col :lg="15" :xs="24">
        <div class="card-shell padded-card">
          <h3 class="section-title">历史消息</h3>
          <el-table :data="notices" v-loading="loading" border>
            <el-table-column prop="title" label="标题" min-width="160" />
            <el-table-column label="类型" min-width="100">
              <template #default="scope">
                <el-tag effect="plain">{{ noticeTypeLabel(scope.row.notice_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="publisher_name" label="发布人" min-width="100" />
            <el-table-column prop="created_at" label="发布时间" min-width="170">
              <template #default="scope">
                {{ formatDateTime(scope.row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column prop="content" label="内容摘要" min-width="240" show-overflow-tooltip />
          </el-table>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { z } from 'zod';

import http from '../../api/http';

const loading = ref(false);
const submitting = ref(false);

const classes = ref([]);
const students = ref([]);
const notices = ref([]);

const form = reactive({
  title: '',
  content: '',
  notice_type: 'CLASS',
  class_id: null,
  target_user_id: null
});

const noticeSchema = z.object({
  title: z.string().min(2, '标题至少2位').max(120),
  content: z.string().min(4, '内容至少4位').max(2000),
  notice_type: z.enum(['CLASS', 'PERSONAL', 'ANNOUNCEMENT', 'RESOURCE']),
  class_id: z.number().int().nullable(),
  target_user_id: z.number().int().nullable()
});

const noticeTypeLabel = (value) => {
  if (value === 'CLASS') return '班级通知';
  if (value === 'PERSONAL') return '个人消息';
  if (value === 'RESOURCE') return '学习资料';
  return '公告通知';
};

const formatDateTime = (value) => new Date(value).toLocaleString();

const loadBase = async () => {
  const [classRes, studentRes] = await Promise.all([http.get('/teacher/classes'), http.get('/teacher/students')]);
  classes.value = classRes.data;
  students.value = studentRes.data;
};

const loadNotices = async () => {
  loading.value = true;
  try {
    const { data } = await http.get('/teacher/notices');
    notices.value = data;
  } finally {
    loading.value = false;
  }
};

const submitNotice = async () => {
  const payload = {
    title: form.title.trim(),
    content: form.content.trim(),
    notice_type: form.notice_type,
    class_id: form.notice_type === 'CLASS' || form.notice_type === 'RESOURCE' ? Number(form.class_id) || null : null,
    target_user_id: form.notice_type === 'PERSONAL' ? Number(form.target_user_id) || null : null
  };

  const parsed = noticeSchema.safeParse(payload);
  if (!parsed.success) {
    ElMessage.warning(parsed.error.issues[0].message);
    return;
  }

  if ((payload.notice_type === 'CLASS' || payload.notice_type === 'RESOURCE') && !payload.class_id) {
    ElMessage.warning('班级通知或学习资料需选择班级');
    return;
  }
  if (payload.notice_type === 'PERSONAL' && !payload.target_user_id) {
    ElMessage.warning('个人消息需选择目标学生');
    return;
  }

  submitting.value = true;
  try {
    await http.post('/teacher/notices', parsed.data);
    ElMessage.success('消息发布成功');
    form.title = '';
    form.content = '';
    form.class_id = null;
    form.target_user_id = null;
    await loadNotices();
  } finally {
    submitting.value = false;
  }
};

onMounted(async () => {
  await loadBase();
  await loadNotices();
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

.section-title {
  margin: 0 0 12px;
  font-size: 18px;
}
</style>
