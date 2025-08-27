import { useQuery } from "@tanstack/react-query";
import { ProfilesApi, Configuration } from "@sdk";
import { tgFetch } from "@/lib/tgFetch";
import { API_BASE } from "@/api/base";

const api = new ProfilesApi(
  new Configuration({ basePath: API_BASE, fetchApi: tgFetch }),
);

export function usePlan(telegramId: number) {
  return useQuery({
    queryKey: ["plan", telegramId],
    queryFn: async () => {
      const profile: any = await api.profilesGet({ telegramId });
      return profile?.plan as string;
    },
  });
}
