import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    reporters: ["default", "json"],
    outputFile: {
      json: "./test-reports/results.json",
    },
  },
});
