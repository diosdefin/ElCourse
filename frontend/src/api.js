// frontend/src/api.js
import axios from 'axios';
import router from './router';

const api = axios.create({
    // Убедись, что адрес совпадает с твоим бэкендом. 
    // Если все запросы идут на /api, лучше добавить его сюда:
    baseURL: 'http://127.0.0.1:8000/api', 
});

// 1. ПЕРЕХВАТЧИК ЗАПРОСОВ (Request Interceptor)
// Этот блок автоматически добавляет токен в каждый твой запрос к бэкенду
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// 2. ПЕРЕХВАТЧИК ОТВЕТОВ (Response Interceptor)
// Твой код, но немного доработанный для стабильности
api.interceptors.response.use(
    (response) => response,
    (error) => {
        // Проверяем, что ошибка именно 401 и мы НЕ на странице логина
        if (error.response && error.response.status === 401) {
            console.warn("Сессия истекла. Очистка данных...");
            
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');

            // Проверяем текущий путь через router.currentRoute.value.path
            if (router.currentRoute.value.path !== '/login') {
                alert('Ваша сессия истекла. Войдите заново');
                router.push('/login');
            }
        }
        return Promise.reject(error);
    }
);

export default api;