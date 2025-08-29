import { afterEach, describe, expect, it, vi } from "vitest";
import { getProfile, saveProfile } from "../src/api/profile";
import { patchProfile } from "../src/features/profile/api";

vi.mock("@/lib/telegram-auth", () => ({
  getTelegramAuthHeaders: () => ({}),
}));

describe("profile api", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("throws error when getProfile request fails", async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValue(new Response("boom", { status: 400 }));
    vi.stubGlobal("fetch", mockFetch);

    await expect(getProfile(1)).rejects.toThrow(
      "Не удалось получить профиль: boom",
    );
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/profiles?telegramId=1",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("throws error when getProfile returns invalid JSON", async () => {
    const mockFetch = vi.fn().mockResolvedValue(
      new Response("not-json", {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", mockFetch);

    await expect(getProfile(1)).rejects.toThrow(
      "Не удалось получить профиль: некорректный ответ сервера",
    );
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/profiles?telegramId=1",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("throws error when saveProfile request fails", async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValue(new Response("fail", { status: 500 }));
    vi.stubGlobal("fetch", mockFetch);

    await expect(
      saveProfile({
        telegramId: 1,
        icr: 1,
        cf: 2,
        target: 5,
        low: 4,
        high: 10,
      }),
    ).rejects.toThrow("Не удалось сохранить профиль: fail");
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/profiles",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("throws error when patchProfile request fails", async () => {
    const mockFetch = vi
      .fn()
      .mockResolvedValue(new Response("fail", { status: 500 }));
    vi.stubGlobal("fetch", mockFetch);

    await expect(
      patchProfile({ timezone: "Europe/Moscow", auto_detect_timezone: true }),
    ).rejects.toThrow("Не удалось обновить профиль: fail");
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/profile",
      expect.objectContaining({ method: "PATCH" }),
    );
  });
});
