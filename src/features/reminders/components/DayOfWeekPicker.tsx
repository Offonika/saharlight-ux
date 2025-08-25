import React from "react";
const NAMES = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"];

export function DayOfWeekPicker({
  value, onChange,
}: { value?: number[]; onChange: (v?: number[]) => void }) {
  const set = new Set(value ?? []);
  const toggle = (d: number) => {
    const next = new Set(set);
    next.has(d) ? next.delete(d) : next.add(d);
    const arr = Array.from(next).sort((a,b)=>a-b);
    onChange(arr.length ? arr : undefined);
  };
  return (
    <div className="flex flex-wrap gap-2">
      {NAMES.map((n, i) => {
        const d = i+1, active = set.has(d);
        return (
          <button
            key={d} type="button" onClick={()=>toggle(d)}
            className={`px-3 py-1 rounded-2xl border text-sm ${active ? "bg-black text-white border-black" : "border-gray-300"}`}
          >{n}</button>
        );
      })}
    </div>
  );
}