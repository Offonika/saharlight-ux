import { DefaultApi, Reminder } from '../../../../libs/ts-sdk';

const api = new DefaultApi();

export async function getReminders(telegramId = 1) {
  const { data } = await api.remindersGet(telegramId);
  return data;
}

export async function updateReminder(payload: Reminder & { id: number }) {
  const { data } = await api.remindersPost(payload);
  return { ...data, id: Number(data.id) };
}

export async function createReminder(payload: Reminder) {
  const { data } = await api.remindersPost(payload);
  return { ...data, id: Number(data.id) };
}
