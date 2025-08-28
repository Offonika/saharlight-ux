
// Mock server для тестирования в режиме разработки
const STORAGE_KEY = 'mockReminders';

function loadFromStorage(): any[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

function saveToStorage(reminders: any[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(reminders));
  } catch {
    // ignore storage errors
  }
}

let mockReminders: any[] = loadFromStorage();
let nextId = Math.max(...mockReminders.map(r => r.id), 0) + 1;

// Initialize with after-meal 30min reminder if it doesn't exist
function initializeDefaultReminders() {
  const telegramId = 12345;
  const hasAfterMeal30 = mockReminders.some(r => 
    r.telegramId === telegramId && 
    r.type === "after_meal" && 
    r.kind === "after_event" && 
    r.minutesAfter === 30
  );
  
  if (!hasAfterMeal30) {
    const newReminder = {
      id: nextId++,
      telegramId,
      type: "after_meal",
      title: null,
      kind: "after_event",
      time: null,
      intervalMinutes: null,
      minutesAfter: 30,
      daysOfWeek: null,
      isEnabled: true,
      nextAt: null,
    };
    mockReminders.push(newReminder);
    saveToStorage(mockReminders);
    console.log('[MockAPI] Added after-meal 30min reminder');
  }
}

// Initialize on load
initializeDefaultReminders();

export const mockApi = {
  async getReminders(telegramId: number) {
    console.log('[MockAPI] Getting reminders for telegram ID:', telegramId);
    console.log('[MockAPI] All reminders:', mockReminders);
    const filtered = mockReminders.filter(r => r.telegramId === telegramId);
    console.log('[MockAPI] Filtered reminders:', filtered);
    return filtered;
  },

  async createReminder(reminder: any) {
    console.log('[MockAPI] Creating reminder:', reminder);

    // Determine kind based on payload data
    let kind: "at_time" | "every" | "after_event" = "at_time";
    if (reminder.time) {
      kind = "at_time";
    } else if (reminder.intervalMinutes || reminder.intervalHours) {
      kind = "every";
    } else if (reminder.minutesAfter) {
      kind = "after_event";
    }

    const newReminder = {
      id: nextId++,
      telegramId: reminder.telegramId,
      type: reminder.type,
      title: reminder.title || null,
      kind,
      time: reminder.time || null,
      intervalMinutes: reminder.intervalMinutes || (reminder.intervalHours ? Math.round(reminder.intervalHours * 60) : null),
      minutesAfter: reminder.minutesAfter || null,
      daysOfWeek: reminder.daysOfWeek ? Array.from(reminder.daysOfWeek) : null,
      isEnabled: reminder.isEnabled,
      nextAt: reminder.nextAt || null,
    };
    mockReminders.push(newReminder);
    saveToStorage(mockReminders);
    return { id: newReminder.id, status: 'ok' };
  },

  async updateReminder(reminder: any) {
    console.log('[MockAPI] Updating reminder:', reminder);
    const index = mockReminders.findIndex(r => r.id === reminder.id);
    if (index >= 0) {
      // Determine kind based on payload data
      let kind: "at_time" | "every" | "after_event" = mockReminders[index].kind;
      if (reminder.time) {
        kind = "at_time";
      } else if (reminder.intervalMinutes || reminder.intervalHours) {
        kind = "every";
      } else if (reminder.minutesAfter) {
        kind = "after_event";
      }

      const updated = {
        ...mockReminders[index],
        type: reminder.type ?? mockReminders[index].type,
        kind,
        time: reminder.time ?? null,
        intervalMinutes: reminder.intervalHours
          ? Math.round(reminder.intervalHours * 60)
          : reminder.intervalMinutes ?? mockReminders[index].intervalMinutes,
        minutesAfter: reminder.minutesAfter ?? mockReminders[index].minutesAfter,
        isEnabled: reminder.isEnabled !== undefined ? reminder.isEnabled : mockReminders[index].isEnabled,
        title: reminder.title ?? mockReminders[index].title,
        daysOfWeek: reminder.daysOfWeek
          ? Array.from(reminder.daysOfWeek)
          : mockReminders[index].daysOfWeek,
      };
      mockReminders[index] = updated;
      saveToStorage(mockReminders);
    }
    return { id: reminder.id, status: 'ok' };
  },

  async deleteReminder(telegramId: number, id: number) {
    console.log('[MockAPI] Deleting reminder:', id);
    mockReminders = mockReminders.filter(r => !(r.id === id && r.telegramId === telegramId));
    saveToStorage(mockReminders);
    return { status: 'ok' };
  },

  async getReminder(telegramId: number, id: number) {
    console.log('[MockAPI] Getting single reminder:', id);
    return mockReminders.find(r => r.id === id && r.telegramId === telegramId) || null;
  }
};
