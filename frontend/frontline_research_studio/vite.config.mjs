import { defineConfig } from "vite";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";

const currentDir = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  root: currentDir,
  publicDir: false,
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        entryFileNames: "assets/frontline-research-studio.js",
        chunkFileNames: "assets/[name].js",
        assetFileNames: (assetInfo) => {
          if (String(assetInfo.name || "").endsWith(".css")) {
            return "assets/frontline-research-studio.css";
          }
          return "assets/[name][extname]";
        }
      }
    }
  }
});
