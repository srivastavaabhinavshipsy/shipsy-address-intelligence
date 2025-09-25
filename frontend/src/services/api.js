import axios from 'axios';
import { API_URL } from '../config';

// API base URL
const API_BASE_URL = `${API_URL}/api`;

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: false,
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    console.log('API Response:', response.data);
    return response;
  },
  (error) => {
    console.error('API Error Details:', {
      message: error.message,
      response: error.response?.data,
      status: error.response?.status,
      url: error.config?.url
    });
    return Promise.reject(error);
  }
);

export const addressAPI = {
  // Validate single address
  validateSingle: async (address) => {
    const response = await api.post('/validate-single', { address });
    return response.data;
  },

  // Validate batch
  validateBatch: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await api.post('/validate-batch', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Get batch status
  getBatchStatus: async (jobId) => {
    const response = await api.get(`/batch-status/${jobId}`);
    return response.data;
  },

  // Download results
  downloadResults: async (jobId) => {
    const response = await api.get(`/download-results/${jobId}`, {
      responseType: 'blob',
    });
    return response.data;
  },

  // Get sample data
  getSampleData: async () => {
    const response = await api.get('/sample-data');
    return response.data;
  },

  // Get provinces
  getProvinces: async () => {
    const response = await api.get('/provinces');
    return response.data;
  },

  // Get stats
  getStats: async () => {
    const response = await api.get('/stats');
    return response.data;
  },

  // Health check
  healthCheck: async () => {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;