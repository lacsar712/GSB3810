<template>
  <div class="page-space">
    <header class="head-block">
      <h2 class="page-title">题库资源管理</h2>
      <p class="page-subtitle">上传、分类、维护教学题库资源，供教师侧按条件检索。</p>
    </header>

    <div class="card-shell padded-card">
      <div class="toolbar">
        <el-input
          v-model="filters.keyword"
          class="custom-input"
          placeholder="输入资源标题关键词"
          clearable
          style="width: 220px"
        />
        <el-select v-model="filters.subject" class="custom-select" clearable placeholder="科目" style="width: 140px">
          <el-option v-for="item in subjects" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="filters.grade" class="custom-select" clearable placeholder="年级" style="width: 120px">
          <el-option v-for="item in grades" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="filters.status" class="custom-select" clearable placeholder="状态" style="width: 120px">
          <el-option label="启用" value="ACTIVE" />
          <el-option label="禁用" value="DISABLED" />
        </el-select>
        <div class="toolbar-right">
          <el-button @click="loadResources">查询</el-button>
          <el-button type="primary" @click="openCreate">新增资源</el-button>
        </div>
      </div>

      <el-table :data="resources" v-loading="loading" border>
        <el-table-column prop="title" label="标题" min-width="200" />
        <el-table-column prop="subject" label="科目" min-width="90" />
        <el-table-column prop="grade" label="年级" min-width="90" />
        <el-table-column prop="tags" label="标签" min-width="150" />
        <el-table-column label="状态" min-width="100">
          <template #default="scope">
            <el-tag :type="scope.row.status === 'ACTIVE' ? 'success' : 'info'">
              {{ scope.row.status === 'ACTIVE' ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="180" fixed="right">
          <template #default="scope">
            <el-button type="primary" link @click="openEdit(scope.row)">编辑</el-button>
            <el-button type="danger" link @click="deleteResource(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialog.visible" :title="dialog.mode === 'create' ? '新增题库资源' : '编辑题库资源'" width="620px">
      <el-form label-position="top">
        <el-form-item label="标题">
          <el-input v-model="dialog.form.title" class="custom-input" maxlength="150" placeholder="请输入资源标题" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="科目">
              <el-select v-model="dialog.form.subject" class="custom-select" placeholder="请选择科目">
                <el-option v-for="item in subjects" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="年级">
              <el-select v-model="dialog.form.grade" class="custom-select" placeholder="请选择年级">
                <el-option v-for="item in grades" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="状态" v-if="dialog.mode === 'edit'">
              <el-select v-model="dialog.form.status" class="custom-select" placeholder="请选择状态">
                <el-option label="启用" value="ACTIVE" />
                <el-option label="禁用" value="DISABLED" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="标签">
          <el-input v-model="dialog.form.tags" class="custom-input" maxlength="200" placeholder="例如：函数,压轴题" />
        </el-form-item>
        <el-form-item label="资源链接">
          <el-input v-model="dialog.form.resource_url" class="custom-input" maxlength="255" placeholder="请输入可访问的资源链接" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="dialog.form.description"
            class="custom-input"
            maxlength="2000"
            type="textarea"
            :rows="4"
            placeholder="请输入资源描述"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="dialog.submitting" @click="submitResource">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { z } from 'zod';

import http from '../../api/http';

const loading = ref(false);
const resources = ref([]);
const subjects = ['语文', '数学', '英语', '物理', '化学', '生物'];
const grades = ['高一', '高二', '高三'];

const filters = reactive({
  keyword: '',
  subject: '',
  grade: '',
  status: ''
});

const dialog = reactive({
  visible: false,
  mode: 'create',
  resourceId: null,
  submitting: false,
  form: {
    title: '',
    subject: '',
    grade: '',
    tags: '',
    resource_url: '',
    description: '',
    status: 'ACTIVE'
  }
});

const createSchema = z.object({
  title: z.string().min(2, '标题至少2位').max(150, '标题长度不能超过150位'),
  subject: z.string().min(1, '请选择科目'),
  grade: z.string().min(1, '请选择年级'),
  tags: z.string().max(200).optional(),
  resource_url: z.string().url('请输入正确的资源链接').max(255),
  description: z.string().min(4, '描述至少4位').max(2000)
});

const updateSchema = createSchema.extend({
  status: z.enum(['ACTIVE', 'DISABLED'])
});

const loadResources = async () => {
  loading.value = true;
  try {
    const { data } = await http.get('/admin/question-resources', {
      params: {
        keyword: filters.keyword || undefined,
        subject: filters.subject || undefined,
        grade: filters.grade || undefined,
        status: filters.status || undefined
      }
    });
    resources.value = data;
  } finally {
    loading.value = false;
  }
};

const openCreate = () => {
  dialog.mode = 'create';
  dialog.resourceId = null;
  dialog.form = {
    title: '',
    subject: '',
    grade: '',
    tags: '',
    resource_url: '',
    description: '',
    status: 'ACTIVE'
  };
  dialog.visible = true;
};

const openEdit = (row) => {
  dialog.mode = 'edit';
  dialog.resourceId = row.id;
  dialog.form = {
    title: row.title,
    subject: row.subject,
    grade: row.grade,
    tags: row.tags || '',
    resource_url: row.resource_url,
    description: row.description,
    status: row.status
  };
  dialog.visible = true;
};

const submitResource = async () => {
  const payload = {
    title: dialog.form.title.trim(),
    subject: dialog.form.subject,
    grade: dialog.form.grade,
    tags: dialog.form.tags.trim() || null,
    resource_url: dialog.form.resource_url.trim(),
    description: dialog.form.description.trim(),
    status: dialog.form.status
  };

  const parsed = dialog.mode === 'create' ? createSchema.safeParse(payload) : updateSchema.safeParse(payload);
  if (!parsed.success) {
    ElMessage.warning(parsed.error.issues[0].message);
    return;
  }

  dialog.submitting = true;
  try {
    if (dialog.mode === 'create') {
      await http.post('/admin/question-resources', parsed.data);
    } else {
      await http.put(`/admin/question-resources/${dialog.resourceId}`, parsed.data);
    }
    dialog.visible = false;
    await loadResources();
    ElMessage.success('保存成功');
  } finally {
    dialog.submitting = false;
  }
};

const deleteResource = async (row) => {
  try {
    await ElMessageBox.confirm('删除后将无法恢复，确认继续？', '删除确认', {
      type: 'warning',
      confirmButtonText: '确认',
      cancelButtonText: '取消'
    });
  } catch (error) {
    if (error === 'cancel' || error === 'close') {
      return;
    }
    throw error;
  }

  await http.delete(`/admin/question-resources/${row.id}`);
  ElMessage.success('删除成功');
  await loadResources();
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
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.toolbar-right {
  margin-left: auto;
  display: flex;
  gap: 8px;
}
</style>
