import { defineConfig } from "vite";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const currentDir = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  root: currentDir,
  publicDir: false,
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        entryFileNames: "assets/workspace-shell-app.js",
        chunkFileNames: "assets/[name].js",
        assetFileNames: (assetInfo) => {
          if (String(assetInfo.name || "").endsWith(".css")) {
            return "assets/workspace-shell-app.css";
          }
          return "assets/[name][extname]";
        }
      }
    }
  },
  resolve: {
    alias: {
      "@demo": resolve(currentDir, "../../demo")
    }
  }
});
