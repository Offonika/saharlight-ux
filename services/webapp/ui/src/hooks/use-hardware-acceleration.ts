import { useEffect, useState } from "react";

export const isHardwareAccelerationEnabled = (): boolean => {
  const canvas = document.createElement("canvas");
  const gl =
    canvas.getContext("webgl2") ||
    canvas.getContext("webgl") ||
    canvas.getContext("experimental-webgl");

  if (!gl) {
    return false;
  }

  const debugInfo = (gl as WebGLRenderingContext).getExtension(
    "WEBGL_debug_renderer_info",
  ) as WebGLDebugRendererInfo | null;

  if (debugInfo) {
    const renderer = (gl as WebGLRenderingContext).getParameter(
      debugInfo.UNMASKED_RENDERER_WEBGL,
    ) as string;
    if (/swiftshader|software|llvmpipe/i.test(renderer)) {
      return false;
    }
  }

  return true;
};

export const useHardwareAcceleration = (): boolean => {
  const [enabled, setEnabled] = useState(true);

  useEffect(() => {
    setEnabled(isHardwareAccelerationEnabled());
  }, []);

  return enabled;
};

export default useHardwareAcceleration;
