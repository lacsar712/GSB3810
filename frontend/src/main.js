import { createApp } from 'vue';
import { createPinia } from 'pinia';
import ElementPlus, { ElMessage } from 'element-plus';
import 'element-plus/dist/index.css';

import App from './App.vue';
import router from './router';
import { useAuthStore } from './store/auth';
import './styles/global.css';

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);

const authStore = useAuthStore();
authStore.loadFromStorage();

app.config.errorHandler = (error) => {
  ElMessage.error(error?.message || '页面渲染出现异常，请稍后重试');
};

app.use(router);
app.use(ElementPlus);
app.mount('#app');
