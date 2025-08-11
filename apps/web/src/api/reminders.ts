export interface ReminderPayload {
  type: string;
  text: string;
  value: string;
  id?: number;
}

const API_BASE = '/api';

export async function getReminders() {
  const res = await fetch(`${API_BASE}/reminders`);
  if (!res.ok) {
    throw new Error('Failed to fetch reminders');
  }
  return res.json();
}

export async function updateReminder(payload: ReminderPayload & { id: number }) {
  const res = await fetch(`/reminders`, {
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
  const res = await fetch(`/reminders`, {
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
