<template>
  <div class="page-space">
    <header class="head-block">
      <h2 class="page-title">学生信息与在校表现</h2>
      <p class="page-subtitle">维护学生档案、更新基础信息，并记录奖惩与课堂表现。</p>
    </header>

    <div class="card-shell padded-card">
      <div class="toolbar">
        <el-select
          v-model="filters.class_id"
          class="custom-select"
          clearable
          placeholder="选择班级"
          style="width: 180px"
        >
          <el-option v-for="item in classes" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-input
          v-model="filters.keyword"
          class="custom-input"
          placeholder="输入姓名或学号"
          clearable
          style="width: 220px"
          @keyup.enter="loadStudents"
        />
        <el-button @click="loadStudents">查询</el-button>
      </div>

      <el-table :data="students" v-loading="loading" border>
        <el-table-column prop="student_no" label="学号" min-width="120" />
        <el-table-column prop="full_name" label="姓名" min-width="110" />
        <el-table-column prop="gender" label="性别" min-width="80" />
        <el-table-column prop="class_name" label="班级" min-width="130" />
        <el-table-column prop="enrollment_year" label="入学年份" min-width="100" />
        <el-table-column prop="address" label="地址" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" min-width="200" fixed="right">
          <template #default="scope">
            <el-button type="primary" link @click="openEdit(scope.row)">编辑信息</el-button>
            <el-button type="warning" link @click="openBehavior(scope.row)">在校表现</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="editDialog.visible" title="编辑学生信息" width="620px">
      <el-form label-position="top">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="姓名">
              <el-input v-model="editDialog.form.full_name" class="custom-input" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="性别">
              <el-select v-model="editDialog.form.gender" class="custom-select">
                <el-option label="男" value="男" />
                <el-option label="女" value="女" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="入学年份">
              <el-input-number v-model="editDialog.form.enrollment_year" :min="2000" :max="2100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="班级">
              <el-select v-model="editDialog.form.class_id" class="custom-select" placeholder="请选择班级">
                <el-option v-for="item in classes" :key="item.id" :label="item.name" :value="item.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="地址">
          <el-input v-model="editDialog.form.address" class="custom-input" maxlength="200" />
        </el-form-item>
        <el-form-item label="家校备注">
          <el-input
            v-model="editDialog.form.guardian_note"
            class="custom-input"
            maxlength="500"
            type="textarea"
            :rows="3"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="editDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="editDialog.submitting" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="behaviorDrawer.visible" size="560px" title="学生在校表现" direction="rtl">
      <div class="drawer-head">
        <h3>{{ behaviorDrawer.studentName || '学生' }}</h3>
        <p>{{ behaviorDrawer.studentNo }}</p>
      </div>

      <div class="drawer-form card-shell padded-card">
        <h4>新增记录</h4>
        <el-form label-position="top">
          <el-form-item label="类别">
            <el-select v-model="behaviorDrawer.form.category" class="custom-select" placeholder="请选择类别">
              <el-option label="奖励" value="REWARD" />
              <el-option label="惩戒" value="PUNISHMENT" />
              <el-option label="观察" value="OBSERVATION" />
            </el-select>
          </el-form-item>
          <el-form-item label="标题">
            <el-input v-model="behaviorDrawer.form.title" class="custom-input" maxlength="100" />
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="behaviorDrawer.form.description" class="custom-input" maxlength="500" type="textarea" :rows="2" />
          </el-form-item>
          <el-row :gutter="10">
            <el-col :span="12">
              <el-form-item label="加减分">
                <el-input-number v-model="behaviorDrawer.form.score_delta" :min="-20" :max="20" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="记录日期">
                <el-date-picker v-model="behaviorDrawer.form.record_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-button type="primary" :loading="behaviorDrawer.submitting" @click="submitBehavior">提交记录</el-button>
        </el-form>
      </div>

      <div class="drawer-list card-shell padded-card">
        <h4>历史记录</h4>
        <el-timeline>
          <el-timeline-item v-for="item in behaviorDrawer.items" :key="item.id" :timestamp="item.record_date">
            <p class="timeline-title">{{ item.title }}（{{ categoryLabel(item.category) }}）</p>
            <p class="timeline-desc">{{ item.description }}</p>
            <p class="timeline-score">分值变化：{{ item.score_delta }}</p>
          </el-timeline-item>
        </el-timeline>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { z } from 'zod';

import http from '../../api/http';

const loading = ref(false);
const students = ref([]);
const classes = ref([]);

const filters = reactive({
  class_id: null,
  keyword: ''
});

const editDialog = reactive({
  visible: false,
  studentId: null,
  submitting: false,
  form: {
    full_name: '',
    gender: '男',
    birth_date: null,
    enrollment_year: 2025,
    address: '',
    guardian_note: '',
    class_id: null
  }
});

const behaviorDrawer = reactive({
  visible: false,
  studentId: null,
  studentName: '',
  studentNo: '',
  items: [],
  submitting: false,
  form: {
    category: 'OBSERVATION',
    title: '',
    description: '',
    score_delta: 0,
    record_date: ''
  }
});

const studentSchema = z.object({
  full_name: z.string().min(2, '姓名至少2位').max(100),
  gender: z.string().min(1),
  birth_date: z.string().nullable(),
  enrollment_year: z.number().int().min(2000).max(2100),
  address: z.string().max(200).nullable(),
  guardian_note: z.string().max(500).nullable(),
  class_id: z.number().int().positive()
});

const behaviorSchema = z.object({
  student_id: z.number().int().positive(),
  category: z.enum(['REWARD', 'PUNISHMENT', 'OBSERVATION']),
  title: z.string().min(2, '标题至少2位').max(100),
  description: z.string().min(4, '描述至少4位').max(500),
  score_delta: z.number().int().min(-20).max(20),
  record_date: z.string().min(1, '请选择记录日期')
});

const categoryLabel = (value) => {
  if (value === 'REWARD') return '奖励';
  if (value === 'PUNISHMENT') return '惩戒';
  return '观察';
};

const loadClasses = async () => {
  const { data } = await http.get('/teacher/classes');
  classes.value = data;
};

const loadStudents = async () => {
  loading.value = true;
  try {
    const { data } = await http.get('/teacher/students', {
      params: {
        class_id: filters.class_id || undefined,
        keyword: filters.keyword || undefined
      }
    });
    students.value = data;
  } finally {
    loading.value = false;
  }
};

const openEdit = (row) => {
  editDialog.studentId = row.id;
  editDialog.form = {
    full_name: row.full_name,
    gender: row.gender,
    birth_date: null,
    enrollment_year: row.enrollment_year,
    address: row.address || '',
    guardian_note: row.guardian_note || '',
    class_id: row.class_id
  };
  editDialog.visible = true;
};

const submitEdit = async () => {
  const payload = {
    full_name: editDialog.form.full_name.trim(),
    gender: editDialog.form.gender,
    birth_date: editDialog.form.birth_date,
    enrollment_year: Number(editDialog.form.enrollment_year),
    address: editDialog.form.address.trim() || null,
    guardian_note: editDialog.form.guardian_note.trim() || null,
    class_id: Number(editDialog.form.class_id)
  };

  const parsed = studentSchema.safeParse(payload);
  if (!parsed.success) {
    ElMessage.warning(parsed.error.issues[0].message);
    return;
  }

  editDialog.submitting = true;
  try {
    await http.put(`/teacher/students/${editDialog.studentId}`, parsed.data);
    editDialog.visible = false;
    ElMessage.success('学生信息已更新');
    await loadStudents();
  } finally {
    editDialog.submitting = false;
  }
};

const loadBehaviorItems = async () => {
  const { data } = await http.get(`/teacher/students/${behaviorDrawer.studentId}/behaviors`);
  behaviorDrawer.items = data;
};

const openBehavior = async (row) => {
  behaviorDrawer.visible = true;
  behaviorDrawer.studentId = row.id;
  behaviorDrawer.studentName = row.full_name;
  behaviorDrawer.studentNo = row.student_no;
  behaviorDrawer.form = {
    category: 'OBSERVATION',
    title: '',
    description: '',
    score_delta: 0,
    record_date: new Date().toISOString().slice(0, 10)
  };
  await loadBehaviorItems();
};

const submitBehavior = async () => {
  const payload = {
    student_id: Number(behaviorDrawer.studentId),
    category: behaviorDrawer.form.category,
    title: behaviorDrawer.form.title.trim(),
    description: behaviorDrawer.form.description.trim(),
    score_delta: Number(behaviorDrawer.form.score_delta),
    record_date: behaviorDrawer.form.record_date
  };

  const parsed = behaviorSchema.safeParse(payload);
  if (!parsed.success) {
    ElMessage.warning(parsed.error.issues[0].message);
    return;
  }

  behaviorDrawer.submitting = true;
  try {
    await http.post('/teacher/behaviors', parsed.data);
    ElMessage.success('表现记录已保存');
    behaviorDrawer.form.title = '';
    behaviorDrawer.form.description = '';
    behaviorDrawer.form.score_delta = 0;
    await loadBehaviorItems();
  } finally {
    behaviorDrawer.submitting = false;
  }
};

onMounted(async () => {
  await loadClasses();
  await loadStudents();
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

.drawer-head h3 {
  margin: 0;
  font-size: 20px;
}

.drawer-head p {
  margin: 4px 0 12px;
  color: #667086;
}

.drawer-form,
.drawer-list {
  margin-top: 12px;
}

.timeline-title {
  margin: 0;
  font-weight: 600;
}

.timeline-desc {
  margin: 6px 0;
  color: #626b7d;
}

.timeline-score {
  margin: 0;
  color: #93311f;
}
</style>
