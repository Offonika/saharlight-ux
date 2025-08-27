import { useQuery } from "@tanstack/react-query";

import { RemindersApi } from "@sdk";
import { Configuration } from "@sdk/runtime";
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
