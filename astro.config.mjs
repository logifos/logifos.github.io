import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://logifos.github.io',
  output: 'static',
  build: { format: 'file' },
});
