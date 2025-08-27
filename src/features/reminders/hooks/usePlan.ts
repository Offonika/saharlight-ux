import { Configuration } from "../../../../libs/ts-sdk/runtime.ts";
import { DefaultApi } from "../../../../libs/ts-sdk/apis";

export async function getPlanLimit(userId: number, initData: string): Promise<number> {
  try {
    // Для демо возвращаем статичные лимиты пока нет API роли
    // TODO: Когда появится API для получения роли пользователя, заменить на реальный вызов
    const limits: Record<string, number> = { 
      free: 5, 
      pro: 10,
      premium: 20 
    };
    
    // Временная логика определения роли по userId
    // В реальном приложении здесь будет вызов API
    const roleString = userId === 12345 ? "free" : "free";
    
    return limits[roleString] ?? 5;
  } catch (error) {
    console.warn("Failed to get plan limit, defaulting to free tier:", error);
    return 5;
  }
}
