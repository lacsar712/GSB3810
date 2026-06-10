<template>
  <div class="page-space">
    <header class="head-block">
      <h2 class="page-title">成绩录入与发布</h2>
      <p class="page-subtitle">按考试维度录入成绩，支持修改、发布与排名自动更新。</p>
    </header>

    <div class="card-shell padded-card">
      <div class="toolbar">
        <el-select v-model="filters.class_id" class="custom-select" clearable placeholder="班级" style="width: 180px">
          <el-option v-for="item in classes" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
        <el-select v-model="filters.subject" class="custom-select" clearable placeholder="科目" style="width: 140px">
          <el-option v-for="item in subjects" :key="item" :label="item" :value="item" />
        </el-select>
        <el-button @click="loadExams">查询考试</el-button>
        <el-button type="primary" @click="openExamDialog">新建考试</el-button>
      </div>

      <el-table :data="exams" v-loading="examLoading" border @row-click="selectExam">
        <el-table-column prop="name" label="考试名称" min-width="160" />
        <el-table-column prop="exam_type" label="类型" min-width="90" />
        <el-table-column prop="subject" label="科目" min-width="90" />
        <el-table-column prop="class_name" label="班级" min-width="120" />
        <el-table-column prop="exam_date" label="考试日期" min-width="120" />
        <el-table-column label="发布状态" min-width="100">
          <template #default="scope">
            <el-tag :type="scope.row.is_published ? 'success' : 'warning'">
              {{ scope.row.is_published ? '已发布' : '未发布' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="card-shell padded-card" v-if="selectedExam">
      <div class="editor-head">
        <div>
          <h3>{{ selectedExam.name }} · {{ selectedExam.subject }} · {{ selectedExam.class_name }}</h3>
          <p class="page-subtitle">输入分数后保存，再执行发布同步排名。</p>
        </div>
        <div class="toolbar-right">
          <el-button :loading="scoreSaving" type="primary" @click="saveScores">保存成绩</el-button>
          <el-button :loading="publishLoading" type="warning" @click="publishScores">发布成绩</el-button>
        </div>
      </div>

      <el-table :data="scoreRows" v-loading="scoreLoading" border>
        <el-table-column prop="student_no" label="学号" min-width="120" />
        <el-table-column prop="full_name" label="姓名" min-width="110" />
        <el-table-column label="成绩" min-width="140">
          <template #default="scope">
            <el-input-number
              v-model="scope.row.score"
              :min="0"
              :max="100"
              :step="0.5"
              controls-position="right"
              style="width: 110px"
            />
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="210">
          <template #default="scope">
            <el-input v-model="scope.row.comment" class="custom-input" maxlength="255" placeholder="输入评语（可选）" />
          </template>
        </el-table-column>
        <el-table-column prop="rank" label="排名" min-width="80" />
      </el-table>
    </div>

    <el-dialog v-model="examDialog.visible" title="新建考试" width="560px">
      <el-form label-position="top">
        <el-form-item label="考试名称">
          <el-input v-model="examDialog.form.name" class="custom-input" maxlength="120" placeholder="请输入考试名称" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="考试类型">
              <el-select v-model="examDialog.form.exam_type" class="custom-select" placeholder="请选择考试类型">
                <el-option label="月考" value="MONTHLY" />
                <el-option label="期中" value="MIDTERM" />
                <el-option label="期末" value="FINAL" />
                <el-option label="测验" value="QUIZ" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="科目">
              <el-select v-model="examDialog.form.subject" class="custom-select" placeholder="请选择科目">
                <el-option v-for="item in subjects" :key="item" :label="item" :value="item" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="年级">
              <el-select v-model="examDialog.form.grade" class="custom-select" placeholder="请选择年级">
                <el-option label="高一" value="高一" />
                <el-option label="高二" value="高二" />
                <el-option label="高三" value="高三" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="班级">
              <el-select v-model="examDialog.form.class_id" class="custom-select" placeholder="请选择班级">
                <el-option v-for="item in classes" :key="item.id" :label="item.name" :value="item.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="考试日期">
          <el-date-picker v-model="examDialog.form.exam_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="examDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="examDialog.submitting" @click="createExam">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { z } from 'zod';

import http from '../../api/http';

const subjects = ['语文', '数学', '英语', '物理', '化学', '生物'];

const classes = ref([]);
const exams = ref([]);
const selectedExam = ref(null);
const scoreRows = ref([]);

const filters = reactive({
  class_id: null,
  subject: ''
});

const examLoading = ref(false);
const scoreLoading = ref(false);
const scoreSaving = ref(false);
const publishLoading = ref(false);

const examDialog = reactive({
  visible: false,
  submitting: false,
  form: {
    name: '',
    exam_type: 'MONTHLY',
    subject: '',
    grade: '高一',
    class_id: null,
    exam_date: ''
  }
});

const examSchema = z.object({
  name: z.string().min(2, '考试名称至少2位').max(120),
  exam_type: z.string().min(2).max(30),
  subject: z.string().min(1, '请选择科目').max(30),
  grade: z.string().min(1, '请选择年级').max(20),
  class_id: z.number().int().positive(),
  exam_date: z.string().min(1, '请选择考试日期')
});

const loadClasses = async () => {
  const { data } = await http.get('/teacher/classes');
  classes.value = data;
};

const loadExams = async () => {
  examLoading.value = true;
  try {
    const { data } = await http.get('/teacher/exams', {
      params: {
        class_id: filters.class_id || undefined,
        subject: filters.subject || undefined
      }
    });
    exams.value = data;
  } finally {
    examLoading.value = false;
  }
};

const selectExam = async (exam) => {
  selectedExam.value = exam;
  await loadScoreRows();
};

const loadScoreRows = async () => {
  if (!selectedExam.value) {
    return;
  }
  scoreLoading.value = true;
  try {
    const [scoreRes, studentRes] = await Promise.all([
      http.get(`/teacher/exams/${selectedExam.value.id}/scores`),
      http.get('/teacher/students', { params: { class_id: selectedExam.value.class_id } })
    ]);

    const scoreMap = new Map(scoreRes.data.map((item) => [item.student_id, item]));
    scoreRows.value = studentRes.data.map((student) => {
      const existing = scoreMap.get(student.id);
      return {
        student_id: student.id,
        student_no: student.student_no,
        full_name: student.full_name,
        score: existing ? Number(existing.score) : null,
        comment: existing?.comment || '',
        rank: existing?.rank || null
      };
    });
  } finally {
    scoreLoading.value = false;
  }
};

const saveScores = async () => {
  if (!selectedExam.value) return;

  const rows = scoreRows.value.filter((row) => row.score !== null && row.score !== undefined);
  if (!rows.length) {
    ElMessage.warning('请至少录入一条成绩');
    return;
  }

  const invalid = rows.find((item) => Number(item.score) < 0 || Number(item.score) > 100);
  if (invalid) {
    ElMessage.warning('成绩必须在 0 到 100 之间');
    return;
  }

  scoreSaving.value = true;
  try {
    await http.post(`/teacher/exams/${selectedExam.value.id}/scores`, {
      scores: rows.map((item) => ({
        student_id: item.student_id,
        score: Number(item.score),
        comment: item.comment ? item.comment.trim() : null
      }))
    });
    ElMessage.success('成绩已保存');
    await loadScoreRows();
    await loadExams();
  } finally {
    scoreSaving.value = false;
  }
};

const publishScores = async () => {
  if (!selectedExam.value) return;
  publishLoading.value = true;
  try {
    await http.post(`/teacher/exams/${selectedExam.value.id}/publish`);
    ElMessage.success('成绩已发布');
    await loadScoreRows();
    await loadExams();
  } finally {
    publishLoading.value = false;
  }
};

const openExamDialog = () => {
  examDialog.form = {
    name: '',
    exam_type: 'MONTHLY',
    subject: '',
    grade: '高一',
    class_id: null,
    exam_date: ''
  };
  examDialog.visible = true;
};

const createExam = async () => {
  const payload = {
    name: examDialog.form.name.trim(),
    exam_type: examDialog.form.exam_type,
    subject: examDialog.form.subject,
    grade: examDialog.form.grade,
    class_id: Number(examDialog.form.class_id),
    exam_date: examDialog.form.exam_date
  };

  const parsed = examSchema.safeParse(payload);
  if (!parsed.success) {
    ElMessage.warning(parsed.error.issues[0].message);
    return;
  }

  examDialog.submitting = true;
  try {
    await http.post('/teacher/exams', parsed.data);
    examDialog.visible = false;
    ElMessage.success('考试创建成功');
    await loadExams();
  } finally {
    examDialog.submitting = false;
  }
};

onMounted(async () => {
  await loadClasses();
  await loadExams();
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

.editor-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  gap: 10px;
  flex-wrap: wrap;
}

.editor-head h3 {
  margin: 0;
  font-size: 18px;
}

.toolbar-right {
  display: flex;
  gap: 8px;
}
</style>
