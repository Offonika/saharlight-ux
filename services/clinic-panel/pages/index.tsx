import { useEffect } from 'react';
import { DefaultApi } from '@offonika/diabetes-ts-sdk';

export default function Home() {
  useEffect(() => {
    const api = new DefaultApi();
    api.healthGet().then((res) => {
      console.log('API client ready', res);
    }).catch((err) => {
      console.error('API client error', err);
    });
  }, []);

  return <main>Clinic Panel</main>;
}
