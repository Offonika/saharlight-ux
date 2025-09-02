import ru from './locales/ru';

const dictionary = ru as Record<string, unknown>;

function get(obj: any, path: string): any {
  return path.split('.').reduce((acc, part) => (acc as any)?.[part], obj);
}

export function useTranslation(namespace?: string) {
  const t = (key: string): string => {
    const fullKey = namespace ? `${namespace}.${key}` : key;
    const value = get(dictionary, fullKey);
    return typeof value === 'string' ? value : fullKey;
  };
  return { t };
}
