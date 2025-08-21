const url = import.meta.env.VITE_API_URL?.trim();
export const API_BASE = url ? url.replace(/\/$/, '') : '/api';
