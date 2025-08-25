import { useState } from "react";
import { deleteReminder } from "@/api/reminders";
import { useTelegram } from "@/hooks/useTelegram";
import { useToast } from "@/hooks/use-toast";

interface Reminder {
  id: number;
  title: string;
}

export default function RemindersList({
  initialReminders,
}: {
  initialReminders: Reminder[];
}) {
  const { user } = useTelegram();
  const { toast } = useToast();
  const [reminders, setReminders] = useState<Reminder[]>(initialReminders);

  const handleDelete = async (id: number) => {
    if (!user?.id) return;
    const prevReminders = [...reminders];
    setReminders(prev => prev.filter(r => r.id !== id));
    try {
      await deleteReminder(user.id, id);
      toast({
        title: "Напоминание удалено",
        description: "Напоминание успешно удалено",
      });
    } catch (err) {
      setReminders(prevReminders);
      const message =
        err instanceof Error ? err.message : "Не удалось удалить напоминание";
      toast({
        title: "Ошибка",
        description: message,
        variant: "destructive",
      });
    }
  };

  return (
    <div className="space-y-3">
      {reminders.map(reminder => (
        <div key={reminder.id} className="flex items-center justify-between">
          <span>{reminder.title}</span>
          <button onClick={() => handleDelete(reminder.id)}>Удалить</button>
        </div>
      ))}
    </div>
  );
}
