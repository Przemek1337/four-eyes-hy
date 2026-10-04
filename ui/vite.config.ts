import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";

export default defineConfig(({ mode }) => {
  // GATEWAY=http://host:port npm run dev  points the dashboard at another gateway
  const gateway = loadEnv(mode, ".", "").GATEWAY ?? "http://127.0.0.1:8080";
  return {
    base: "/ui/",
    plugins: [react()],
    build: { outDir: "../src/foureyes/ui_dist", emptyOutDir: true },
    server: { port: 5173, proxy: { "/admin": gateway, "/metrics": gateway, "/audit": gateway, "/__mock": gateway } },
    test: { environment: "jsdom", globals: true, setupFiles: ["./src/test/setup.ts"], css: false },
  };
});
