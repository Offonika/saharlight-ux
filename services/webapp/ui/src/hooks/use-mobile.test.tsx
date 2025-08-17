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
    act(() => {
      TestRenderer.create(<TestComponent />);
    });
    expect(result).toBe(false);
  }, { environment: "node" });
});
