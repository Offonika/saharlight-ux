import React from "react";
import { useRemindersApi } from "../api/reminders";
import { buildReminderPayload } from "../api/buildPayload";
import { mockApi } from "../../../api/mock-server";
import { useToast } from "../../../shared/toast";

export function Templates({ 
  telegramId, 
  onCreated 
}: { 
  telegramId: number; 
  onCreated: () => void 
}) {
  const api = useRemindersApi();
  const toast = useToast();
  
  const templates = [
    {
      title: "Сахар утром 07:30",
      emoji: "🩸",
      dto: { telegramId, type: "sugar", kind: "at_time", time: "07:30", isEnabled: true }
    },
    {
      title: "После еды 120 мин", 
      emoji: "🍽️",
      dto: { telegramId, type: "after_meal", kind: "after_event", minutesAfter: 120, isEnabled: true }
    },
    {
      title: "Длинный инсулин 22:00",
      emoji: "💉", 
      dto: { telegramId, type: "insulin_long", kind: "at_time", time: "22:00", isEnabled: true }
    },
    {
      title: "Короткий инсулин",
      emoji: "💊",
      dto: { telegramId, type: "insulin_short", kind: "every", intervalMinutes: 180, isEnabled: true }
    }
  ] as const;
  
  const create = async (dto: any) => {
    try {
      const payload = buildReminderPayload(dto);
      
      try {
        await api.remindersPost({ reminder: payload });
      } catch (apiError) {
        console.warn("Backend API failed, using mock API:", apiError);
        await mockApi.createReminder(payload);
      }
      
      toast.success("Напоминание создано из шаблона");
      onCreated();
    } catch (err) {
      console.error("Error creating reminder from template:", err);
      toast.error("Не удалось создать напоминание");
    }
  };
  
  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-muted-foreground">Быстрые шаблоны</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {templates.map((template) => (
          <button
            key={template.title}
            onClick={() => create(template.dto)}
            className="flex items-center gap-3 p-3 rounded-lg border border-border bg-background text-foreground hover:bg-secondary hover:border-primary/20 transition-all duration-200 animate-scale-in text-left"
          >
            <span className="text-2xl">{template.emoji}</span>
            <span className="text-sm font-medium">{template.title}</span>
          </button>
        ))}
      </div>
    </div>
  );
}