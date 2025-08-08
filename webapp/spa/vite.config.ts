import { defineConfig } from "vite";

export default defineConfig({
  base: "/ui/",
  build: {
    outDir: "../ui",
    emptyOutDir: true,
  },
});
