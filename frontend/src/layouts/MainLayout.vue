<template>
  <div class="layout-root">
    <aside class="side-menu card-shell" v-if="!isMobile">
      <div class="brand-block">
        <p class="brand-cn">星河教务</p>
        <p class="brand-en">School Affairs</p>
      </div>
      <el-menu :default-active="activePath" class="menu-panel" router>
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>
    </aside>

    <main class="main-area">
      <header class="topbar card-shell">
        <div class="left-wrap">
          <el-button v-if="isMobile" class="mobile-menu-btn" @click="drawerVisible = true" text>
            菜单
          </el-button>
          <div>
            <h1 class="heading">高中教务管理系统</h1>
            <p class="subheading">{{ roleLabel }} · {{ authStore.user?.full_name || '未登录' }}</p>
          </div>
        </div>
        <el-button type="danger" plain @click="logout">退出登录</el-button>
      </header>

      <section class="content-area">
        <router-view v-slot="{ Component }">
          <transition name="fade-slide" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </section>
    </main>

    <el-drawer v-model="drawerVisible" direction="ltr" size="250px" :with-header="false">
      <div class="brand-block mobile">
        <p class="brand-cn">星河教务</p>
        <p class="brand-en">School Affairs</p>
      </div>
      <el-menu :default-active="activePath" class="menu-panel" router @select="drawerVisible = false">
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { useAuthStore } from '../store/auth';

const authStore = useAuthStore();
const route = useRoute();
const router = useRouter();

const isMobile = ref(window.innerWidth < 980);
const drawerVisible = ref(false);

const resizeHandler = () => {
  isMobile.value = window.innerWidth < 980;
  if (!isMobile.value) {
    drawerVisible.value = false;
  }
};

onMounted(() => {
  window.addEventListener('resize', resizeHandler);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeHandler);
});

const roleLabel = computed(() => {
  if (authStore.user?.role === 'ADMIN') {
    return '总管理员端';
  }
  return '教师端';
});

const menuItems = computed(() => {
  if (authStore.user?.role === 'ADMIN') {
    return [
      { path: '/admin/dashboard', label: '管理总览' },
      { path: '/admin/teachers', label: '教师账号管理' },
      { path: '/admin/resources', label: '题库资源管理' },
      { path: '/admin/system', label: '系统配置与备份' }
    ];
  }

  return [
    { path: '/teacher/dashboard', label: '教学总览' },
    { path: '/teacher/students', label: '学生信息管理' },
    { path: '/teacher/scores', label: '成绩管理发布' },
    { path: '/teacher/notices', label: '消息通知发布' },
    { path: '/teacher/analytics', label: '成绩分析可视化' },
    { path: '/teacher/resources', label: '题库搜索' }
  ];
});

const activePath = computed(() => route.path);

const logout = () => {
  authStore.clearAuth();
  router.push('/login');
};
</script>

<style scoped>
.layout-root {
  min-height: 100vh;
  padding: 16px;
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 16px;
}

.side-menu {
  padding: 18px 14px;
  border-radius: 18px;
  background: linear-gradient(185deg, #fffaf4 0%, #fafbff 65%, #fff2ee 100%);
}

.brand-block {
  margin-bottom: 14px;
  padding: 12px 12px 14px;
  border-radius: 14px;
  background: linear-gradient(120deg, #ffe9db, #eef3ff);
}

.brand-cn {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  font-family: 'ZCOOL XiaoWei', serif;
  color: #30211a;
}

.brand-en {
  margin: 4px 0 0;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #8b6a5a;
}

.menu-panel {
  border-right: none;
  background: transparent;
}

.main-area {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  border-radius: 16px;
}

.left-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.mobile-menu-btn {
  margin-right: 6px;
}

.heading {
  margin: 0;
  font-size: 21px;
}

.subheading {
  margin: 2px 0 0;
  color: #6a7281;
  font-size: 13px;
}

.content-area {
  flex: 1;
  min-height: 0;
}

@media (max-width: 979px) {
  .layout-root {
    grid-template-columns: 1fr;
    padding: 10px;
  }

  .topbar {
    padding: 12px;
  }

  .heading {
    font-size: 18px;
  }
}
</style>
