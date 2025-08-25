import React from "react";

const DAYS = [
  { value: 1, name: "Пн", label: "Понедельник" },
  { value: 2, name: "Вт", label: "Вторник" },
  { value: 3, name: "Ср", label: "Среда" },
  { value: 4, name: "Чт", label: "Четверг" },
  { value: 5, name: "Пт", label: "Пятница" },
  { value: 6, name: "Сб", label: "Суббота" },
  { value: 0, name: "Вс", label: "Воскресенье" },
];

export function DayOfWeekPicker({
  value, 
  onChange,
}: { 
  value?: number[]; 
  onChange: (v?: number[]) => void 
}) {
  const selectedSet = new Set(value ?? []);
  
  const toggle = (dayValue: number) => {
    const nextSet = new Set(selectedSet);
    nextSet.has(dayValue) ? nextSet.delete(dayValue) : nextSet.add(dayValue);
    const sortedArray = Array.from(nextSet).sort((a, b) => a - b);
    onChange(sortedArray.length ? sortedArray : undefined);
  };

  return (
    <div className="flex flex-wrap gap-2">
      {DAYS.map(day => {
        const isSelected = selectedSet.has(day.value);
        return (
          <button
            key={day.value} 
            type="button" 
            onClick={() => toggle(day.value)}
            className={`px-3 py-2 rounded-lg border text-sm font-medium transition-all duration-200 ${
              isSelected 
                ? "bg-primary text-primary-foreground border-primary shadow-soft" 
                : "border-border bg-background text-foreground hover:bg-secondary hover:border-primary/20"
            }`}
            title={day.label}
          >
            {day.name}
          </button>
        );
      })}
    </div>
  );
}