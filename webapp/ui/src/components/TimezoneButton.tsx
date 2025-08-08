// webapp/ui/src/components/TimezoneButton.tsx
import React from "react";
import { useTimezone } from "../hooks/useTimezone";

export default function TimezoneButton() {
  const { tz, submit, detect } = useTimezone();

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm opacity-80">Часовой пояс: {tz || "—"}</span>
      <button className="px-3 py-1 rounded-lg border" onClick={() => detect()}>
        Определить заново
      </button>
      <button className="px-3 py-1 rounded-lg border" onClick={() => submit()}>
        Сохранить
      </button>
    </div>
  );
}
