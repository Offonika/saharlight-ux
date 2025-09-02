import ru from './locales/ru';

const dictionary: Record<string, unknown> = ru;

function get(obj: Record<string, unknown>, path: string): unknown {
  return path.split('.').reduce<unknown>((acc, key) => {
    if (acc && typeof acc === 'object' && key in (acc as Record<string, unknown>)) {
      return (acc as Record<string, unknown>)[key];
    }
    return undefined;
  }, obj);
}

export function useTranslation(namespace?: string) {
  const t = (key: string): string => {
    const fullKey = namespace ? `${namespace}.${key}` : key;
    const result = get(dictionary, fullKey);
    return typeof result === 'string' ? result : fullKey;
  };
  return { t };
}
