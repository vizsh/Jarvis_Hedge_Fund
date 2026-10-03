import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Every backend route needs an entry here. Adding an endpoint to FastAPI and
    // forgetting this proxy is a silent failure: the dev server answers with the SPA
    // index, the fetch "succeeds", and the feature just never works.
    proxy: Object.fromEntries([
      ["/ws", { target: "ws://localhost:8000", ws: true }],
      ...["/health", "/state", "/policy", "/prices", "/evidence", "/command", "/boot",
          "/stt", "/script", "/recordings", "/replay", "/record", "/calibration", "/universe", "/portfolios", "/profiles",
          "/xray", "/stress", "/ask", "/glossary", "/screen", "/correlation",
          "/rebalance", "/attribution", "/lots", "/history",
          "/tts", "/language", "/translate", "/scan", "/tax", "/firewall", "/sandbox", "/ledger",
          "/funds", "/myfunds", "/scamcall", "/feedrag", "/emergency", "/digest", "/goal", "/panic",
          "/recovery", "/actions", "/flows", "/palette", "/drilldown", "/report", "/watch"]
        .map((route) => [route, "http://localhost:8000"]),
    ]),
  },
  build: { outDir: "dist", chunkSizeWarningLimit: 1400 },
});
