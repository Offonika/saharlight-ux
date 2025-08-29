import { getTelegramAuthHeaders } from "@/lib/telegram-auth";

interface PatchProfileParams {
  timezone: string | null;
  auto_detect_timezone: boolean | null;
}

export async function patchProfile({
  timezone,
  auto_detect_timezone,
}: PatchProfileParams): Promise<unknown> {
  const headers = {
    "Content-Type": "application/json",
    ...getTelegramAuthHeaders(),
  } as HeadersInit;

  try {
    const res = await fetch("/api/profile", {
      method: "PATCH",
      headers,
      body: JSON.stringify({ timezone, auto_detect_timezone }),
    });

    if (!res.ok) {
      const errorText = await res.text().catch(() => "");
      const msg = errorText || "Request failed";
      throw new Error(msg);
    }

    return (await res.json().catch(() => ({}))) as unknown;
  } catch (error) {
    console.error("Failed to update profile:", error);
    if (error instanceof Error) {
      throw new Error(`Не удалось обновить профиль: ${error.message}`);
    }
    throw error;
  }
}
