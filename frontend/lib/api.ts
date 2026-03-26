import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const clinicalApi = {
  async query(query: string) {
    const { data } = await api.post('/query', { query });
    return data;
  },

  async uploadDocument(file: File, type: 'guidelines' | 'drugs' | 'patients') {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await api.post(`/upload/${type}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return data;
  },

  async getStatus() {
    const { data } = await api.get('/status');
    return data;
  },

  async clearData() {
    const { data } = await api.delete('/clear');
    return data;
  },
};
