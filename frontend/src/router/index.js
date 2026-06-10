import { createRouter, createWebHistory } from 'vue-router';

import LoginView from '../views/LoginView.vue';
import MainLayout from '../layouts/MainLayout.vue';
import AdminDashboard from '../views/admin/AdminDashboard.vue';
import AdminTeachersView from '../views/admin/AdminTeachersView.vue';
import AdminResourcesView from '../views/admin/AdminResourcesView.vue';
import AdminSystemView from '../views/admin/AdminSystemView.vue';
import TeacherDashboardView from '../views/teacher/TeacherDashboardView.vue';
import TeacherStudentsView from '../views/teacher/TeacherStudentsView.vue';
import TeacherScoresView from '../views/teacher/TeacherScoresView.vue';
import TeacherNoticesView from '../views/teacher/TeacherNoticesView.vue';
import TeacherAnalyticsView from '../views/teacher/TeacherAnalyticsView.vue';
import TeacherQuestionBankView from '../views/teacher/TeacherQuestionBankView.vue';

const routes = [
  {
    path: '/login',
    name: 'login',
    component: LoginView,
    meta: { public: true }
  },
  {
    path: '/',
    component: MainLayout,
    children: [
      { path: '', redirect: '/teacher/dashboard' },
      { path: 'admin/dashboard', component: AdminDashboard, meta: { roles: ['ADMIN'] } },
      { path: 'admin/teachers', component: AdminTeachersView, meta: { roles: ['ADMIN'] } },
      { path: 'admin/resources', component: AdminResourcesView, meta: { roles: ['ADMIN'] } },
      { path: 'admin/system', component: AdminSystemView, meta: { roles: ['ADMIN'] } },
      { path: 'teacher/dashboard', component: TeacherDashboardView, meta: { roles: ['TEACHER', 'ADMIN'] } },
      { path: 'teacher/students', component: TeacherStudentsView, meta: { roles: ['TEACHER', 'ADMIN'] } },
      { path: 'teacher/scores', component: TeacherScoresView, meta: { roles: ['TEACHER', 'ADMIN'] } },
      { path: 'teacher/notices', component: TeacherNoticesView, meta: { roles: ['TEACHER', 'ADMIN'] } },
      { path: 'teacher/analytics', component: TeacherAnalyticsView, meta: { roles: ['TEACHER', 'ADMIN'] } },
      { path: 'teacher/resources', component: TeacherQuestionBankView, meta: { roles: ['TEACHER', 'ADMIN'] } }
    ]
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('school_token');
  const rawUser = localStorage.getItem('school_user');
  const user = rawUser ? JSON.parse(rawUser) : null;

  if (to.meta.public) {
    if (token && to.path === '/login') {
      if (user?.role === 'ADMIN') {
        next('/admin/dashboard');
        return;
      }
      next('/teacher/dashboard');
      return;
    }
    next();
    return;
  }

  if (!token || !user) {
    next('/login');
    return;
  }

  const allowedRoles = to.meta.roles || [];
  if (allowedRoles.length > 0 && !allowedRoles.includes(user.role)) {
    next(user.role === 'ADMIN' ? '/admin/dashboard' : '/teacher/dashboard');
    return;
  }

  next();
});

export default router;
