export const TIME_REGEX = /^(\d{1,2}):(\d{2})$/

/**
 * Parses HH:MM string to total minutes from midnight.
 * Returns NaN for invalid format or out-of-range values.
 */
export function parseTimeToMinutes(t: string): number {
  const match = TIME_REGEX.exec(t.trim())
  if (!match) return NaN
  const hours = Number(match[1])
  const minutes = Number(match[2])
  if (hours < 0 || hours > 23 || minutes < 0 || minutes > 59) return NaN
  return hours * 60 + minutes
}

/**
 * Checks whether a string matches HH:MM format (no range validation).
 */
export function isValidTimeFormat(t: string): boolean {
  return TIME_REGEX.test(t.trim())
}

/**
 * Validates time string to be within 00:00-23:59 range.
 */
export function isValidTime(t: string): boolean {
  return !Number.isNaN(parseTimeToMinutes(t))
}
