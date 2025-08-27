import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, afterEach } from "vitest";
import React from "react";

import { usePlan } from "./usePlan";

const mockRemindersGet = vi.hoisted(() => vi.fn());

vi.mock(
  "@sdk",
  () => {
    class RemindersApi {
      remindersGet = mockRemindersGet;
    }
    class Configuration {}
    return { RemindersApi, Configuration };
  },
  { virtual: true },
);

function createWrapper() {
  const queryClient = new QueryClient();
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
}

describe("usePlan", () => {
  afterEach(() => {
    mockRemindersGet.mockReset();
  });

  it("is loading initially", () => {
    mockRemindersGet.mockResolvedValueOnce([]);
    const { result } = renderHook(() => usePlan(1), {
      wrapper: createWrapper(),
    });
    expect(result.current.isLoading).toBe(true);
  });

  it("returns data on success", async () => {
    const data = [{ id: 1 }];
    mockRemindersGet.mockResolvedValueOnce(data);
    const { result } = renderHook(() => usePlan(1), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(data);
  });

  it("returns error on failure", async () => {
    const error = new Error("fail");
    mockRemindersGet.mockRejectedValueOnce(error);
    const { result } = renderHook(() => usePlan(1), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBe(error);
  });
});
