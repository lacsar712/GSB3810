<template>
  <div class="page-space">
    <header class="head-block">
      <h2 class="page-title">教师账号管理</h2>
      <p class="page-subtitle">创建、编辑、启停教师账号并设置权限范围。</p>
    </header>

    <div class="card-shell padded-card">
      <div class="toolbar">
        <el-input
          v-model="filters.keyword"
          class="custom-input"
          placeholder="输入教师姓名或账号"
          clearable
          style="width: 260px"
          @keyup.enter="loadTeachers"
        />
        <div class="toolbar-right">
          <el-button @click="loadTeachers">查询</el-button>
          <el-button type="primary" @click="openCreate">新建教师</el-button>
        </div>
      </div>

      <el-table :data="teachers" v-loading="loading" border>
        <el-table-column prop="username" label="账号" min-width="140" />
        <el-table-column prop="full_name" label="姓名" min-width="120" />
        <el-table-column prop="mobile" label="手机号" min-width="140" />
        <el-table-column label="权限" min-width="240">
          <template #default="scope">
            <el-tag
              v-for="perm in scope.row.permissions"
              :key="perm"
              style="margin-right: 6px; margin-bottom: 4px"
              effect="plain"
            >
              {{ perm }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="100">
          <template #default="scope">
            <el-tag :type="scope.row.is_active ? 'success' : 'danger'">
              {{ scope.row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="180" fixed="right">
          <template #default="scope">
            <el-button type="primary" link @click="openEdit(scope.row)">编辑</el-button>
            <el-button type="warning" link @click="toggleStatus(scope.row)">
              {{ scope.row.is_active ? '禁用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialog.visible" :title="dialog.mode === 'create' ? '新建教师账号' : '编辑教师账号'" width="560px">
      <el-form label-position="top">
        <el-form-item label="账号" v-if="dialog.mode === 'create'">
          <el-input v-model="dialog.form.username" class="custom-input" maxlength="50" placeholder="请输入账号" />
        </el-form-item>
        <el-form-item label="密码" v-if="dialog.mode === 'create'">
          <el-input
            v-model="dialog.form.password"
            class="custom-input"
            maxlength="64"
            type="password"
            show-password
            placeholder="请输入密码"
          />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="dialog.form.full_name" class="custom-input" maxlength="100" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="dialog.form.mobile" class="custom-input" maxlength="20" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="权限">
          <el-checkbox-group v-model="dialog.form.permissions">
            <el-checkbox v-for="item in permissionOptions" :key="item" :value="item">
              {{ item }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="dialog.submitting" @click="submitTeacher">保存</el-button>
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
const teachers = ref([]);
const filters = reactive({
  keyword: ''
});

const permissionOptions = ['student:write', 'score:write', 'notice:write', 'analysis:view', 'question_bank:view'];

const dialog = reactive({
  visible: false,
  mode: 'create',
  teacherId: null,
  submitting: false,
  form: {
    username: '',
    password: '',
    full_name: '',
    mobile: '',
    permissions: ['student:write', 'score:write', 'notice:write', 'analysis:view']
  }
});

const createSchema = z.object({
  username: z.string().min(4, '账号至少4位').max(50, '账号长度不能超过50位'),
  password: z.string().min(6, '密码至少6位').max(64, '密码长度不能超过64位'),
  full_name: z.string().min(2, '姓名至少2位').max(100, '姓名长度不能超过100位'),
  mobile: z.string().max(20, '手机号长度不能超过20位').optional(),
  permissions: z.array(z.string())
});

const updateSchema = z.object({
  full_name: z.string().min(2, '姓名至少2位').max(100, '姓名长度不能超过100位'),
  mobile: z.string().max(20, '手机号长度不能超过20位').optional(),
  permissions: z.array(z.string())
});

const loadTeachers = async () => {
  loading.value = true;
  try {
    const { data } = await http.get('/admin/teachers', { params: { keyword: filters.keyword || undefined } });
    teachers.value = data;
  } finally {
    loading.value = false;
  }
};

const openCreate = () => {
  dialog.mode = 'create';
  dialog.teacherId = null;
  dialog.form = {
    username: '',
    password: '',
    full_name: '',
    mobile: '',
    permissions: ['student:write', 'score:write', 'notice:write', 'analysis:view']
  };
  dialog.visible = true;
};

const openEdit = (teacher) => {
  dialog.mode = 'edit';
  dialog.teacherId = teacher.id;
  dialog.form = {
    username: teacher.username,
    password: '',
    full_name: teacher.full_name,
    mobile: teacher.mobile || '',
    permissions: teacher.permissions || []
  };
  dialog.visible = true;
};

const submitTeacher = async () => {
  const payload = {
    username: dialog.form.username.trim(),
    password: dialog.form.password,
    full_name: dialog.form.full_name.trim(),
    mobile: dialog.form.mobile.trim() || null,
    permissions: dialog.form.permissions
  };

  const result = dialog.mode === 'create' ? createSchema.safeParse(payload) : updateSchema.safeParse(payload);
  if (!result.success) {
    ElMessage.warning(result.error.issues[0].message);
    return;
  }

  dialog.submitting = true;
  try {
    if (dialog.mode === 'create') {
      await http.post('/admin/teachers', result.data);
    } else {
      await http.put(`/admin/teachers/${dialog.teacherId}`, result.data);
    }
    dialog.visible = false;
    await loadTeachers();
    ElMessage.success('保存成功');
  } finally {
    dialog.submitting = false;
  }
};

const toggleStatus = async (teacher) => {
  const targetText = teacher.is_active ? '禁用' : '启用';
  try {
    await ElMessageBox.confirm(`确认${targetText}该教师账号？`, '状态变更', {
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

  await http.patch(`/admin/teachers/${teacher.id}/status`, { is_active: !teacher.is_active });
  await loadTeachers();
  ElMessage.success('状态已更新');
};

onMounted(() => {
  loadTeachers();
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
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.toolbar-right {
  display: flex;
  gap: 8px;
}
</style>
