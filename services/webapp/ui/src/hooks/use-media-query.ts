import * as React from 'react';

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = React.useState(false);

  React.useEffect(() => {
    if (typeof window.matchMedia !== 'function') {
      return;
    }
    const mql = window.matchMedia(query);
    const onChange = (event: MediaQueryListEvent) => {
      setMatches(event.matches);
    };
    const useEventListener = typeof mql.addEventListener === 'function';
    if (useEventListener) {
      mql.addEventListener('change', onChange);
    } else {
      // @ts-expect-error -- older browsers
      mql.addListener(onChange);
    }
    setMatches(mql.matches);
    return () => {
      if (useEventListener) {
        mql.removeEventListener('change', onChange);
      } else {
        // @ts-expect-error -- older browsers
        mql.removeListener(onChange);
      }
    };
  }, [query]);

  return matches;
}

export default useMediaQuery;
