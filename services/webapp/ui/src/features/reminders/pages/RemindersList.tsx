import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getReminders, deleteReminder } from "@/api/reminders";
import { useTelegram } from "@/hooks/useTelegram";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import type { Reminder as ApiReminder } from "@sdk";

interface Reminder extends ApiReminder {
  title?: string;
  nextAt?: string;
}

export default function RemindersList() {
  const { user } = useTelegram();
  const navigate = useNavigate();
  const [reminders, setReminders] = useState<Reminder[]>([]);

  useEffect(() => {
    if (!user?.id) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await getReminders(user.id);
        if (!cancelled) setReminders(data as Reminder[]);
      } catch (err) {
        console.error(err);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user?.id]);

  const groups = reminders.reduce<Record<string, Reminder[]>>((acc, r) => {
    (acc[r.type] ||= []).push(r);
    return acc;
  }, {});

  const handleToggle = (id: number, checked: boolean) => {
    setReminders((prev) =>
      prev.map((r) => (r.id === id ? { ...r, isEnabled: checked } : r))
    );
  };

  const handleDelete = async (id: number) => {
    if (!user?.id) return;
    try {
      await deleteReminder(user.id, id);
      setReminders((prev) => prev.filter((r) => r.id !== id));
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-6">
      {Object.entries(groups).map(([type, list]) => (
        <section key={type} className="space-y-2">
          <h2 className="text-lg font-semibold">{type}</h2>
          <div className="space-y-2">
            {list.map((r) => (
              <Card key={r.id}>
                <CardContent className="flex items-start justify-between p-4">
                  <div className="space-y-1">
                    <div className="font-medium">{r.title}</div>
                    <div className="text-sm text-muted-foreground">
                      {r.type} {r.time ?? `${r.intervalHours}h`}
                    </div>
                    {r.nextAt && (
                      <div className="text-sm text-muted-foreground">
                        {new Date(r.nextAt).toLocaleString()}
                      </div>
                    )}
                  </div>
                  <div className="flex flex-col items-end gap-2">
                    <Switch
                      checked={r.isEnabled}
                      onCheckedChange={(checked) =>
                        handleToggle(r.id!, checked)
                      }
                    />
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => navigate(`/reminders/${r.id}/edit`)}
                      >
                        ✏️ ред.
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => handleDelete(r.id!)}
                      >
                        🗑 удалить
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}

