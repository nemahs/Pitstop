import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path, { resolve } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);

const __dirname = path.dirname(__filename);

// https://vite.dev/config/
export default defineConfig((env) => ({
  plugins: [react()],
  base: env.mode === "development" ? "" : "/_vite-static",
  server: {
    host: '127.0.0.1',
    port: 3000,
    open: false,
    watch: {
      usePolling: true,
      disableGlobbing: false,
    },
    origin: env.mode === "development" ? 'http://127.0.0.1:3000' : "",
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
      '/main.js': path.resolve(__dirname, 'src/main.tsx'),
      // /esm/icons/index.mjs only exports the icons statically, so no separate chunks are created
      '@tabler/icons-react': '@tabler/icons-react/dist/esm/icons/index.mjs',
    }
  },
    build: {
    outDir: resolve('./dist'),
    assetsDir: "assets",
    target: 'esnext',
    rollupOptions: {
      input: {
        main: resolve('./src/main.tsx'),
      },
      output: {
        entryFileNames: `assets/bundle.js`,
      },
    },
  },
}))
