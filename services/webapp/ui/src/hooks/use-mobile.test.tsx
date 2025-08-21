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
    const originalWindow = (global as any).window;
    // @ts-expect-error simulate absence of window
    delete (global as any).window;
    act(() => {
      TestRenderer.create(<TestComponent />);
    });
    (global as any).window = originalWindow;
    expect(result).toBe(false);
  });
});
