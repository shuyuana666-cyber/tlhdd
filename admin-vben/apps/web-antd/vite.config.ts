import { defineConfig } from '@vben/vite-config';

export default defineConfig(async () => {
  return {
    application: {},
    vite: {
      base: '/admin/',
      build: {
        outDir: '../../../admin-vben-build',
        emptyOutDir: true,
      },
      server: {
        proxy: {
          '/api': {
            changeOrigin: true,
            target: 'http://127.0.0.1:4173',
            ws: true,
          },
        },
      },
    },
  };
});
