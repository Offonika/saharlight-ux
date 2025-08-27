export function formatLastFiredAt(lastFiredAt?: string | null) {
  if (!lastFiredAt) return "—";
  const d = new Date(lastFiredAt);
  const dd = d.toLocaleDateString(undefined, { day: "2-digit", month: "2-digit" });
  const tt = d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  return `${dd} ${tt}`;
}