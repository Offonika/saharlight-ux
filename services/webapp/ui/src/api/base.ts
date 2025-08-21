const rawUrl = import.meta.env.VITE_API_URL;
const trimmedUrl =
  typeof rawUrl === 'string' ? rawUrl.trim() : undefined;

export const API_BASE =
  trimmedUrl === undefined || trimmedUrl === ''
    ? '/api'
    : trimmedUrl.replace(/\/$/, '');
