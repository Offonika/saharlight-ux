export interface ReminderPayload {
  id?: number;
  type: 'sugar' | 'insulin' | 'meal' | 'medicine';
  title: string;
  time: string;
  interval?: number;
}

const API_BASE = '/api';

export async function updateReminder(payload: ReminderPayload & { id: number }) {
  const res = await fetch(`${API_BASE}/reminders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    throw new Error('Failed to update reminder');
  }
  return res.json();
}

export async function createReminder(payload: ReminderPayload) {
  const res = await fetch(`${API_BASE}/reminders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    throw new Error('Failed to create reminder');
  }
  return res.json();
}
