<template>
  <div class="login-root">
    <div class="ambient-shape one"></div>
    <div class="ambient-shape two"></div>
    <div class="login-card card-shell">
      <div class="title-wrap">
        <p class="badge">WEB PORTAL</p>
        <h1>教务管理入口</h1>
        <p>仅教师与总管理员可通过网页端登录，家长与学生请使用微信小程序。</p>
      </div>

      <el-form :model="form" label-position="top" @submit.prevent>
        <el-form-item label="账号">
          <el-input
            v-model="form.username"
            class="custom-input"
            placeholder="请输入账号"
            maxlength="50"
            autocomplete="username"
          />
        </el-form-item>

        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            class="custom-input"
            type="password"
            show-password
            placeholder="请输入密码"
            maxlength="64"
            autocomplete="current-password"
          />
        </el-form-item>

        <el-button type="primary" class="submit-btn" :loading="loading" @click="handleLogin">
          登录系统
        </el-button>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { z } from 'zod';

import http from '../api/http';
import { useAuthStore } from '../store/auth';

const router = useRouter();
const authStore = useAuthStore();

const loading = ref(false);
const form = reactive({
  username: '',
  password: ''
});

const loginSchema = z.object({
  username: z.string().min(3, '账号至少3位').max(50, '账号长度不能超过50位'),
  password: z.string().min(6, '密码至少6位').max(64, '密码长度不能超过64位')
});

const handleLogin = async () => {
  const validated = loginSchema.safeParse(form);
  if (!validated.success) {
    ElMessage.warning(validated.error.issues[0].message);
    return;
  }

  loading.value = true;
  try {
    const { data } = await http.post('/auth/web-login', validated.data);
    authStore.setAuth(data);

    if (data.user.role === 'ADMIN') {
      await router.push('/admin/dashboard');
    } else {
      await router.push('/teacher/dashboard');
    }
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.login-root {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  position: relative;
  overflow: hidden;
  background: linear-gradient(145deg, #f6f0e8, #f2f6ff 45%, #eff6ee 100%);
}

.ambient-shape {
  position: absolute;
  border-radius: 50%;
  filter: blur(2px);
}

.ambient-shape.one {
  width: 420px;
  height: 420px;
  background: #ffd8c8;
  top: -130px;
  left: -140px;
  opacity: 0.4;
}

.ambient-shape.two {
  width: 360px;
  height: 360px;
  background: #d7e5ff;
  right: -120px;
  bottom: -120px;
  opacity: 0.5;
}

.login-card {
  width: min(92vw, 460px);
  padding: 26px;
  border-radius: 24px;
  position: relative;
  z-index: 1;
  backdrop-filter: blur(2px);
}

.title-wrap {
  margin-bottom: 20px;
}

.badge {
  margin: 0;
  display: inline-block;
  font-size: 11px;
  letter-spacing: 0.16em;
  color: #923826;
  background: #ffe7db;
  border-radius: 999px;
  padding: 4px 10px;
}

.title-wrap h1 {
  margin: 10px 0 8px;
  font-size: 30px;
  font-family: 'ZCOOL XiaoWei', serif;
}

.title-wrap p {
  margin: 0;
  line-height: 1.6;
  color: #5f6778;
}

.submit-btn {
  width: 100%;
  height: 42px;
  margin-top: 4px;
}
</style>
