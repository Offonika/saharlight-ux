import ru from './locales/ru';

const dictionary: Record<string, string> = ru;

export function useTranslation() {
  const t = (key: string): string => dictionary[key] ?? key;
  return { t };
}
