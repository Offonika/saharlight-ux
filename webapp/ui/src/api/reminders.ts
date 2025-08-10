export interface ReminderPayload {
  id?: number;
  type: 'sugar' | 'insulin' | 'meal' | 'medicine';
  title: string;
  time: string;
}

const API_BASE = '/api';

export async function updateReminder(payload: ReminderPayload & { id: number }) {
  const res = await fetch(`${API_BASE}/reminders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...payload, id: Number(payload.id) })
  });
  if (!res.ok) {
    throw new Error('Failed to update reminder');
  }
  const data = await res.json();
  return { ...data, id: Number(data.id) };
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
  const data = await res.json();
  return { ...data, id: Number(data.id) };
}
