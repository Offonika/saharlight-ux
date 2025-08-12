import { useEffect } from 'react';
import { DefaultApi } from 'ts-sdk';

export default function Home() {
  useEffect(() => {
    const api = new DefaultApi();
    console.log('API client ready', api);
  }, []);

  return <main>Clinic Panel</main>;
}
