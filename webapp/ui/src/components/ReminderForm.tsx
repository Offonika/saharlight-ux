import React, { useState } from "react";
import { SegmentedControl, MedicalButton } from "@/components";

type TypeKey = "sugar" | "insulin" | "meal";
const TYPES: Record<TypeKey, { label: string; emoji: string }> = {
  sugar: { label: "Сахар", emoji: "🩸" },
  insulin: { label: "Инсулин", emoji: "💉" },
  meal: { label: "Приём пищи", emoji: "🍽️" },
};

export interface ReminderFormValues {
  type: TypeKey;
  title: string;
  time: string;
  interval: number;
}

export default function ReminderForm(props: {
  onSubmit: (data: ReminderFormValues) => void;
  onCancel?: () => void;
}) {
  const [type, setType] = useState<TypeKey>("sugar");
  const [title, setTitle] = useState("");
  const [time, setTime] = useState("12:30");
  const [interval, setInterval] = useState(60);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        props.onSubmit({ type, title, time, interval });
      }}
      className="mt-2"
    >
      <h2 className="text-lg font-semibold mb-2">Новое напоминание</h2>

      <SegmentedControl
        value={type}
        onChange={(val) => setType(val as TypeKey)}
        items={Object.entries(TYPES).map(([key, v]) => ({
          value: key,
          icon: v.emoji,
          label: v.label,
        }))}
      />

      <label htmlFor="title">Название</label>
      <input
        id="title"
        className="input"
        placeholder="Например: Измерение сахара"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        maxLength={40}
      />

      <div className="grid gap-2 md:grid-cols-2">
        <div>
          <label htmlFor="time">Время</label>
          <input
            id="time"
            className="input"
            type="time"
            value={time}
            onChange={(e) => setTime(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="interval">Интервал (мин)</label>
          <input
            id="interval"
            className="input"
            type="number"
            min={5}
            step={5}
            value={interval}
            onChange={(e) => setInterval(Number(e.target.value))}
            placeholder="Например: 60"
          />
        </div>
      </div>

      <div className="flex gap-2 mt-3">
        <MedicalButton type="submit">Сохранить</MedicalButton>
        <MedicalButton
          type="button"
          variant="secondary"
          onClick={props.onCancel}
        >
          Отмена
        </MedicalButton>
      </div>
    </form>
  );
}
