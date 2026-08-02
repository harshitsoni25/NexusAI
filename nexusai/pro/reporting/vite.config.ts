import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Standalone reporting app. In dev it proxies /api to the existing FastAPI backend
// (no backend changes); with VITE_USE_MOCKS=true it runs fully on mock analytics.
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ["react", "react-dom", "@mui/material", "@mui/icons-material", "@emotion/react", "@emotion/styled"],
        },
      },
    },
  },
  server: { port: 5273, proxy: { "/api": { target: "http://127.0.0.1:8000", changeOrigin: true } } },
});
