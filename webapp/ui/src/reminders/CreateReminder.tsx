import { useState } from "react";
import { useNavigate } from "react-router-dom";
import ReminderForm, { ReminderFormValues } from "@/components/ReminderForm";

export default function CreateReminder() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (values: ReminderFormValues) => {
    setError(null);
    try {
      const res = await fetch("/api/reminders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values)
      });
      if (!res.ok) {
        throw new Error("Failed to create reminder");
      }
      navigate("/reminders");
    } catch {
      setError("Не удалось сохранить напоминание");
    }
  };

  return (
    <div>
      {error && (
        <div className="mb-4 text-destructive">
          {error}
        </div>
      )}
      <ReminderForm onSubmit={handleSubmit} onCancel={() => navigate("/reminders")} />
    </div>
  );
}
