import { defineStore } from 'pinia';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: '',
    user: null
  }),
  getters: {
    isLoggedIn: (state) => Boolean(state.token),
    isAdmin: (state) => state.user?.role === 'ADMIN',
    isTeacher: (state) => state.user?.role === 'TEACHER'
  },
  actions: {
    setAuth(payload) {
      this.token = payload.access_token;
      this.user = payload.user;
      localStorage.setItem('school_token', payload.access_token);
      localStorage.setItem('school_user', JSON.stringify(payload.user));
    },
    loadFromStorage() {
      const token = localStorage.getItem('school_token');
      const user = localStorage.getItem('school_user');
      this.token = token || '';
      this.user = user ? JSON.parse(user) : null;
    },
    clearAuth() {
      this.token = '';
      this.user = null;
      localStorage.removeItem('school_token');
      localStorage.removeItem('school_user');
    }
  }
});
