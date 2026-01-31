/**
 * API client for backend communication
 */

import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const customerAPI = {
  // Get customer context
  getContext: async (customerId) => {
    const response = await api.get(`/customer/${customerId}/context`);
    return response.data;
  },

  // List all customers
  listCustomers: async () => {
    const response = await api.get('/customers');
    return response.data;
  },

  // Submit new conversation
  submitConversation: async (data) => {
    const response = await api.post('/conversation', data);
    return response.data;
  },

  // Transcribe audio
  transcribeAudio: async (file, customerId = null, customerName = null, customerEmail = null, customerPhone = null) => {
    const formData = new FormData();
    formData.append('file', file);
    if (customerId) {
      formData.append('customer_id', customerId);
    }
    if (customerName) {
      formData.append('customer_name', customerName);
    }
    if (customerEmail) {
      formData.append('customer_email', customerEmail);
    }
    if (customerPhone) {
      formData.append('customer_phone', customerPhone);
    }
    const response = await api.post('/transcribe', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Trigger action
  triggerAction: async (actionType, customerId, details = {}) => {
    const response = await api.post('/action/trigger', {
      action_type: actionType,
      customer_id: customerId,
      details: details,
    });
    return response.data;
  },

  // Get pending actions
  getPendingActions: async (limit = 50) => {
    const response = await api.get(`/actions/pending?limit=${limit}`);
    return response.data;
  },

  // Update action status
  updateActionStatus: async (actionId, status) => {
    const response = await api.put(`/action/${actionId}/status?status=${status}`);
    return response.data;
  },

  // Health check
  healthCheck: async () => {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;
