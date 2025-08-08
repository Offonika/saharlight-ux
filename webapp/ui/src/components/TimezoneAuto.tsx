// webapp/ui/src/components/TimezoneAuto.tsx
import { useEffect } from "react";
import { useTimezone } from "../hooks/useTimezone";

export default function TimezoneAuto() {
  const { submit } = useTimezone();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    submit(true);
  }, []);
  return null;
}
