import { describe, expect, it, vi } from "vitest";
import { isHardwareAccelerationEnabled } from "./use-hardware-acceleration";

describe("isHardwareAccelerationEnabled", () => {
  it("returns false when WebGL context is unavailable", () => {
    const original = document.createElement;
    document.createElement = vi
      .fn()
      .mockReturnValue({ getContext: () => null } as unknown as HTMLCanvasElement);
    expect(isHardwareAccelerationEnabled()).toBe(false);
    document.createElement = original;
  });

  it("returns false for software renderers", () => {
    const original = document.createElement;
    document.createElement = vi.fn().mockReturnValue(
      {
        getContext: () => ({
          getExtension: () => ({ UNMASKED_RENDERER_WEBGL: "r" }),
          getParameter: () => "SwiftShader",
        }),
      } as unknown as HTMLCanvasElement,
    );
    expect(isHardwareAccelerationEnabled()).toBe(false);
    document.createElement = original;
  });

  it("returns true for hardware renderers", () => {
    const original = document.createElement;
    document.createElement = vi.fn().mockReturnValue(
      {
        getContext: () => ({
          getExtension: () => ({ UNMASKED_RENDERER_WEBGL: "r" }),
          getParameter: () => "GeForce",
        }),
      } as unknown as HTMLCanvasElement,
    );
    expect(isHardwareAccelerationEnabled()).toBe(true);
    document.createElement = original;
  });
});
