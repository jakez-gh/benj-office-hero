// basic export from API client package

import axios from 'axios';

// shared axios instance pointed at the proxied API root
export const client = axios.create({
  baseURL: '/api'
});

export * from './auth';
