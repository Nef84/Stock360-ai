import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL ?? '/api/v1';

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Request: attach Bearer token ──────────────────────────────────────────────
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('access_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response: auto-refresh on 401 ────────────────────────────────────────────
let isRefreshing = false;
let queue: Array<(token: string) => void> = [];

api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;

      if (isRefreshing) {
        return new Promise((resolve) => {
          queue.push((token) => {
            original.headers.Authorization = `Bearer ${token}`;
            resolve(api(original));
          });
        });
      }

      isRefreshing = true;
      const refreshToken = localStorage.getItem('refresh_token');

      if (!refreshToken) {
        clearSession();
        return Promise.reject(error);
      }

      try {
        const { data } = await axios.post(`${BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });
        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        queue.forEach((cb) => cb(data.access_token));
        queue = [];
        original.headers.Authorization = `Bearer ${data.access_token}`;
        return api(original);
      } catch {
        clearSession();
        return Promise.reject(error);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

function clearSession() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user');
  window.location.href = '/login';
}

// ── Typed helpers ─────────────────────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  refresh: (refresh_token: string) =>
    api.post('/auth/refresh', { refresh_token }),
  createUser: (data: object) => api.post('/auth/users', data),
};

export const productsApi = {
  list:         (params?: object)             => api.get('/products', { params }),
  get:          (id: number)                  => api.get(`/products/${id}`),
  create:       (data: object)                => api.post('/products', data),
  update:       (id: number, data: object)    => api.patch(`/products/${id}`, data),
  importFile:   (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/products/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  adjustStock:  (id: number, delta: number, reason: string) =>
    api.post(`/products/${id}/stock`, { delta, reason }),
};

export const conversationsApi = {
  list:         (params?: object)             => api.get('/conversations', { params }),
  get:          (id: number)                  => api.get(`/conversations/${id}`),
  create:       (data: object)                => api.post('/conversations', data),
  update:       (id: number, data: object)    => api.patch(`/conversations/${id}`, data),
  hide:         (id: number)                  => api.post(`/conversations/${id}/hide`),
  hideClosed:   ()                            => api.post('/conversations/hide-closed'),
  getMessages:  (id: number)                  => api.get(`/conversations/${id}/messages`),
  sendMessage:  (id: number, content: string) =>
    api.post(`/conversations/${id}/messages`, { content, source: 'agent' }),
  aiChat:       (conversation_id: number, customer_message: string) =>
    api.post('/conversations/ai/chat', { conversation_id, customer_message }),
  createCustomer: (data: object)              => api.post('/conversations/customers', data),
};

export const analyticsApi = {
  dashboard:   ()                             => api.get('/analytics/dashboard'),
  salesByDay:  (days = 7)                     => api.get('/analytics/sales-by-day', { params: { days } }),
  topProducts: (days = 30)                    => api.get('/analytics/top-products', { params: { days } }),
  sales:       (params?: object)              => api.get('/sales', { params }),
};
