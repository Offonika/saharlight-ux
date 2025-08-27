import * as React from "react";
import TestRenderer, { act } from "react-test-renderer";
import { describe, expect, it } from "vitest";
import { useIsMobile } from "./use-mobile";

describe("useIsMobile", () => {
  it("returns false when window is undefined", () => {
    let result = true;
    const TestComponent = () => {
      result = useIsMobile();
      return null;
    };
    const globalWithWindow = global as { window?: unknown };
    const originalWindow = globalWithWindow.window;
    // @ts-expect-error simulate absence of window
    delete globalWithWindow.window;
    act(() => {
      TestRenderer.create(<TestComponent />);
    });
    globalWithWindow.window = originalWindow;
    expect(result).toBe(false);
  });
});
