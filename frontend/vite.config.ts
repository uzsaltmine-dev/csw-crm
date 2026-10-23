import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  build: {
    rollupOptions: {
      output: { manualChunks: { react: ["react", "react-dom", "react-router-dom"], mui: ["@mui/material", "@emotion/react", "@emotion/styled"] } },
    },
  },
  server: {
    port: 5173,
    // Lokal ishlab chiqishda backend (uvicorn :8000) ga yo'naltirish
    proxy: {
      "/api": "http://localhost:8000",
      "/socket.io": { target: "http://localhost:8000", ws: true },
    },
  },
});
