import { DefaultApi, Reminder } from "@sdk";

const api = new DefaultApi();

export function useRemindersApi() {
  return {
    createReminder(reminder: Reminder) {
      return api.remindersPost({ reminder });
    },
  };
}

export type { Reminder };
