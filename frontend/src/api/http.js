import axios from 'axios';
import { ElMessage } from 'element-plus';

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 15000
});

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('school_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

http.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error?.response?.data?.message || '请求失败，请检查网络或稍后重试';

    if (error?.response?.status === 401) {
      localStorage.removeItem('school_token');
      localStorage.removeItem('school_user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }

    ElMessage.error(message);
    return Promise.reject(error);
  }
);

export default http;
