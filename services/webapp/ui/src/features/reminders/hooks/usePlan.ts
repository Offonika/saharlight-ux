import { useQuery } from "@tanstack/react-query";
import { RemindersApi, Configuration } from "@sdk";
import { API_BASE } from "@/api/base";
import { tgFetch } from "@/lib/tgFetch";

const api = new RemindersApi(
  new Configuration({ basePath: API_BASE, fetchApi: tgFetch }),
);

export function usePlan(telegramId: number) {
  return useQuery({
    queryKey: ["plan", telegramId],
    queryFn: ({ signal }) => api.remindersGet({ telegramId }, { signal }),
    retry: false,
  });
}
