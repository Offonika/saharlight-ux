import React from "react";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach } from "vitest";

const mockProfilesGet = vi.hoisted(() => vi.fn());

vi.mock(
  "@sdk",
  () => {
    class ProfilesApi {
      profilesGet = mockProfilesGet;
    }
    class Configuration {}
    return { ProfilesApi, Configuration };
  },
  { virtual: true },
);

vi.mock("@/lib/tgFetch", () => ({ tgFetch: vi.fn() }), { virtual: true });
vi.mock("@/api/base", () => ({ API_BASE: "" }), { virtual: true });

import { usePlan } from "./usePlan";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
}

describe("usePlan", () => {
  beforeEach(() => {
    mockProfilesGet.mockReset();
  });

  it("returns plan on success", async () => {
    mockProfilesGet.mockResolvedValueOnce({ plan: "pro" });
    const { result } = renderHook(() => usePlan(1), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBe("pro");
  });

  it("handles error state", async () => {
    const error = new Error("fail");
    mockProfilesGet.mockRejectedValueOnce(error);
    const { result } = renderHook(() => usePlan(1), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.error).toBe(error));
  });

  it("shows loading initially", async () => {
    mockProfilesGet.mockResolvedValueOnce({ plan: "free" });
    const { result } = renderHook(() => usePlan(1), {
      wrapper: createWrapper(),
    });
    expect(result.current.isLoading).toBe(true);
  });
});
