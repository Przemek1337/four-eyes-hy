import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const gateway = "http://127.0.0.1:8080";

export default defineConfig({
  base: "/ui/",
  plugins: [react()],
  build: { outDir: "../src/foureyes/ui_dist", emptyOutDir: true },
  server: { port: 5173, proxy: { "/admin": gateway, "/metrics": gateway, "/audit": gateway } },
  test: { environment: "jsdom", globals: true, setupFiles: ["./src/test/setup.ts"], css: false },
});
