/**
 * Robust date and time formatting utilities ensuring consistent UTC parsing
 * and localized display across all browsers and devices.
 */

export function parseServerDate(iso: string | Date | null | undefined): Date {
  if (!iso) return new Date();
  if (iso instanceof Date) return iso;
  const str = String(iso).trim();
  if (!str) return new Date();

  // If the ISO string has no timezone indicator (no 'Z' and no '+05:30' / '-04:00'),
  // append 'Z' so standard ECMAScript parsers treat it as UTC rather than local time.
  const hasTimezone = str.endsWith('Z') || /[+-]\d{2}(:\d{2})?$/.test(str);
  const normalized = hasTimezone ? str : `${str}Z`;
  const d = new Date(normalized);
  return isNaN(d.getTime()) ? new Date(str) : d;
}

export function formatLocalDateTime(iso: string | Date | null | undefined): string {
  const d = parseServerDate(iso);
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });
}

export function formatLocalTime(iso: string | Date | null | undefined): string {
  const d = parseServerDate(iso);
  return d.toLocaleTimeString(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });
}

export function formatLocalDate(iso: string | Date | null | undefined): string {
  const d = parseServerDate(iso);
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}
