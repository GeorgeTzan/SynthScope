import { sveltekit } from '@sveltejs/kit/vite';
import { svelteTesting } from '@testing-library/svelte/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [sveltekit(), svelteTesting()],
  server: { proxy: { '/api': { target: process.env.API_URL ?? 'http://localhost:8000', ws: true } } },
  test: { environment: 'jsdom', include: ['src/**/*.test.ts'] }
});
