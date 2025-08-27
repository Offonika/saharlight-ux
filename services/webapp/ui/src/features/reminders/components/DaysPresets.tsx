import React from "react";

export function DaysPresets({ 
  value, 
  onChange 
}: {
  value?: number[];
  onChange: (v?: number[]) => void;
}) {
  const eq = (a?: number[], b?: number[]) => 
    JSON.stringify(a ?? []) === JSON.stringify(b ?? []);
  
  const WD = [1, 2, 3, 4, 5]; // Будни
  const WE = [6, 0]; // Выходные (Суббота и Воскресенье)
  const ALL = [1, 2, 3, 4, 5, 6, 0]; // Каждый день
  
  const Btn = ({ label, days }: { label: string; days?: number[] }) => (
    <button 
      type="button"
      onClick={() => onChange(days?.length ? days : undefined)}
      className={`px-3 py-2 rounded-lg border text-sm font-medium transition-all duration-200 ${
        eq(value, days)
          ? "bg-primary text-primary-foreground border-primary shadow-soft" 
          : "border-border bg-background text-foreground hover:bg-secondary hover:border-primary/20"
      }`}
    >
      {label}
    </button>
  );
  
  return (
    <div className="flex gap-2 flex-wrap">
      <Btn label="Каждый день" days={ALL} />
      <Btn label="Будни" days={WD} />
      <Btn label="Выходные" days={WE} />
    </div>
  );
}