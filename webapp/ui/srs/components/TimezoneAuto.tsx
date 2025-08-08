// webapp/ui/src/components/TimezoneAuto.tsx
import { useEffect } from "react";
import { useTimezone } from "../hooks/useTimezone";

export default function TimezoneAuto() {
  const { submit } = useTimezone();
  useEffect(() => { submit(true); }, [submit]);
  return null;
}
