import React, { useState } from "react";

type TypeKey = "sugar" | "insulin" | "meal";
const TYPES: Record<TypeKey, { label: string; emoji: string }> = {
  sugar:   { label: "Сахар",   emoji: "🩸" },
  insulin: { label: "Инсулин", emoji: "💉" },
  meal:    { label: "Приём пищи", emoji: "🍽️" },
};

export default function ReminderForm(props: {
  onSubmit: (data: { type: TypeKey; title: string; time: string; interval: number }) => void;
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
      style={{ marginTop: 8 }}
    >
      <h2>Новое напоминание</h2>

      {/* Тип напоминания в виде сегмента (компактно, влезает на экран) */}
      <div className="segment" role="tablist" aria-label="Тип напоминания">
        {Object.entries(TYPES).map(([key, v]) => (
          <button
            key={key}
            type="button"
            className="chip"
            data-active={type === key}
            onClick={() => setType(key as TypeKey)}
            aria-pressed={type === key}
          >
            <span className="emoji">{v.emoji}</span>
            <span>{v.label}</span>
          </button>
        ))}
      </div>

      <label htmlFor="title">Название</label>
      <input
        id="title"
        className="input"
        placeholder="Например: Измерение сахара"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        maxLength={40}
      />

      <div className="form-grid">
        <div>
          <label htmlFor="time">Время</label>
          <input id="time" className="input" type="time" value={time} onChange={(e)=>setTime(e.target.value)} />
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
            onChange={(e)=>setInterval(Number(e.target.value))}
            placeholder="Например: 60"
          />
        </div>
      </div>

      <div className="actions-row">
        <button className="btn-primary" type="submit">Сохранить</button>
        <button className="btn-ghost" type="button" onClick={props.onCancel}>Отмена</button>
      </div>
    </form>
  );
}
