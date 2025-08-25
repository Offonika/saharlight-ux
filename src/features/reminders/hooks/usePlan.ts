import { Configuration } from "../../../../libs/ts-sdk/runtime";
import { DefaultApi } from "../../../../libs/ts-sdk/apis";

export async function getPlanLimit(userId: number, initData: string): Promise<number> {
  try {
    const cfg = new Configuration({
      basePath: "",
      headers: { "X-Telegram-Init-Data": initData },
    });
    const api = new DefaultApi(cfg);
    
    // Try to get user role from API
    const role: any = await api.getRoleUserUserIdRoleGet(userId);
    const roleString = (role?.role || "free").toLowerCase();
    
    const limits: Record<string, number> = { 
      free: 5, 
      pro: 10,
      premium: 20 
    };
    
    return limits[roleString] ?? 5;
  } catch (error) {
    console.warn("Failed to get plan limit, defaulting to free tier:", error);
    // Default to free tier if API call fails
    return 5;
  }
}