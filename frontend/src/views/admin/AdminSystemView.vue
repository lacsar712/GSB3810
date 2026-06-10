<template>
  <div class="page-space">
    <header class="head-block">
      <h2 class="page-title">系统配置与备份</h2>
      <p class="page-subtitle">维护系统参数、数据字典并执行数据备份与恢复。</p>
    </header>

    <el-row :gutter="16">
      <el-col :lg="14" :xs="24">
        <div class="card-shell padded-card section-box">
          <div class="section-head">
            <h3>系统配置</h3>
          </div>
          <el-table :data="configs" v-loading="configLoading" border>
            <el-table-column prop="config_key" label="配置键" min-width="160" />
            <el-table-column prop="config_value" label="配置值" min-width="180" />
            <el-table-column prop="description" label="说明" min-width="140" />
            <el-table-column label="操作" min-width="80" fixed="right">
              <template #default="scope">
                <el-button type="primary" link @click="openConfigDialog(scope.row)">编辑</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>

      <el-col :lg="10" :xs="24">
        <div class="card-shell padded-card section-box">
          <div class="section-head">
            <h3>新增数据字典</h3>
          </div>
          <el-form label-position="top">
            <el-form-item label="字典类型">
              <el-input v-model="dictForm.dict_type" class="custom-input" placeholder="例如 exam_type" maxlength="50" />
            </el-form-item>
            <el-form-item label="字典键">
              <el-input v-model="dictForm.dict_key" class="custom-input" placeholder="例如 MONTHLY" maxlength="50" />
            </el-form-item>
            <el-form-item label="字典值">
              <el-input v-model="dictForm.dict_value" class="custom-input" placeholder="例如 月考" maxlength="100" />
            </el-form-item>
            <el-form-item label="排序">
              <el-input-number v-model="dictForm.sort_order" :min="0" :max="999" />
            </el-form-item>
            <el-button type="primary" :loading="dictSubmitting" @click="createDictionary">新增字典</el-button>
          </el-form>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :lg="12" :xs="24">
        <div class="card-shell padded-card section-box">
          <div class="section-head">
            <h3>数据字典列表</h3>
          </div>
          <el-table :data="dictionaries" v-loading="dictLoading" border max-height="340">
            <el-table-column prop="dict_type" label="类型" min-width="100" />
            <el-table-column prop="dict_key" label="键" min-width="110" />
            <el-table-column prop="dict_value" label="值" min-width="100" />
            <el-table-column prop="sort_order" label="排序" min-width="80" />
          </el-table>
        </div>
      </el-col>

      <el-col :lg="12" :xs="24">
        <div class="card-shell padded-card section-box">
          <div class="section-head">
            <h3>数据备份与恢复</h3>
            <el-button type="primary" :loading="backupCreating" @click="createBackup">立即备份</el-button>
          </div>

          <el-table :data="backups" v-loading="backupLoading" border max-height="340">
            <el-table-column prop="file_name" label="备份文件" min-width="190" />
            <el-table-column label="状态" min-width="100">
              <template #default="scope">
                <el-tag :type="scope.row.status === 'READY' ? 'success' : 'warning'">
                  {{ scope.row.status === 'READY' ? '可恢复' : '已恢复' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" min-width="120" fixed="right">
              <template #default="scope">
                <el-button type="warning" link @click="restoreBackup(scope.row)">恢复</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
    </el-row>

    <el-dialog v-model="configDialog.visible" title="编辑系统配置" width="520px">
      <el-form label-position="top">
        <el-form-item label="配置键">
          <el-input :value="configDialog.form.config_key" disabled />
        </el-form-item>
        <el-form-item label="配置值">
          <el-input
            v-model="configDialog.form.config_value"
            class="custom-input"
            type="textarea"
            :rows="3"
            maxlength="2000"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="configDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="configDialog.submitting" @click="submitConfig">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { z } from 'zod';

import http from '../../api/http';

const configs = ref([]);
const dictionaries = ref([]);
const backups = ref([]);

const configLoading = ref(false);
const dictLoading = ref(false);
const backupLoading = ref(false);

const dictSubmitting = ref(false);
const backupCreating = ref(false);

const dictForm = reactive({
  dict_type: '',
  dict_key: '',
  dict_value: '',
  sort_order: 0,
  is_active: true
});

const configDialog = reactive({
  visible: false,
  submitting: false,
  form: {
    config_key: '',
    config_value: ''
  }
});

const dictSchema = z.object({
  dict_type: z.string().min(1, '字典类型不能为空').max(50),
  dict_key: z.string().min(1, '字典键不能为空').max(50),
  dict_value: z.string().min(1, '字典值不能为空').max(100),
  sort_order: z.number().int().min(0).max(999),
  is_active: z.boolean()
});

const configSchema = z.object({
  config_value: z.string().min(1, '配置值不能为空').max(2000)
});

const loadConfigs = async () => {
  configLoading.value = true;
  try {
    const { data } = await http.get('/admin/configs');
    configs.value = data;
  } finally {
    configLoading.value = false;
  }
};

const loadDictionaries = async () => {
  dictLoading.value = true;
  try {
    const { data } = await http.get('/admin/dictionaries');
    dictionaries.value = data;
  } finally {
    dictLoading.value = false;
  }
};

const loadBackups = async () => {
  backupLoading.value = true;
  try {
    const { data } = await http.get('/admin/backups');
    backups.value = data;
  } finally {
    backupLoading.value = false;
  }
};

const openConfigDialog = (row) => {
  configDialog.form = {
    config_key: row.config_key,
    config_value: row.config_value
  };
  configDialog.visible = true;
};

const submitConfig = async () => {
  const payload = { config_value: configDialog.form.config_value.trim() };
  const parsed = configSchema.safeParse(payload);
  if (!parsed.success) {
    ElMessage.warning(parsed.error.issues[0].message);
    return;
  }

  configDialog.submitting = true;
  try {
    await http.put(`/admin/configs/${configDialog.form.config_key}`, parsed.data);
    configDialog.visible = false;
    ElMessage.success('配置已更新');
    await loadConfigs();
  } finally {
    configDialog.submitting = false;
  }
};

const createDictionary = async () => {
  const payload = {
    dict_type: dictForm.dict_type.trim(),
    dict_key: dictForm.dict_key.trim(),
    dict_value: dictForm.dict_value.trim(),
    sort_order: Number(dictForm.sort_order || 0),
    is_active: dictForm.is_active
  };

  const parsed = dictSchema.safeParse(payload);
  if (!parsed.success) {
    ElMessage.warning(parsed.error.issues[0].message);
    return;
  }

  dictSubmitting.value = true;
  try {
    await http.post('/admin/dictionaries', parsed.data);
    ElMessage.success('字典新增成功');
    dictForm.dict_type = '';
    dictForm.dict_key = '';
    dictForm.dict_value = '';
    dictForm.sort_order = 0;
    await loadDictionaries();
  } finally {
    dictSubmitting.value = false;
  }
};

const createBackup = async () => {
  backupCreating.value = true;
  try {
    await http.post('/admin/backups');
    ElMessage.success('备份创建成功');
    await loadBackups();
  } finally {
    backupCreating.value = false;
  }
};

const restoreBackup = async (row) => {
  try {
    await ElMessageBox.confirm('恢复备份会覆盖当前数据，确认继续？', '风险确认', {
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

  await http.post(`/admin/backups/${row.id}/restore`);
  ElMessage.success('数据恢复完成');
  await Promise.all([loadConfigs(), loadDictionaries(), loadBackups()]);
};

onMounted(() => {
  Promise.all([loadConfigs(), loadDictionaries(), loadBackups()]);
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

.section-box {
  min-height: 320px;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-head h3 {
  margin: 0;
  font-size: 18px;
}
</style>
