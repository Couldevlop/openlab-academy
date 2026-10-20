import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// Paquet servi par Frappe sous /assets/openlab_academy/espace/ ; noms fixes, la page www/espace.html les charge.
export default defineConfig({
  plugins: [vue()],
  base: '/assets/openlab_academy/espace/',
  resolve: {
    alias: {
      // seule la requête Frappe de frappe-ui (jeton CSRF, erreurs) : ses composants ne sont pas embarqués
      'frappe-ui-requete': fileURLToPath(new URL('./node_modules/frappe-ui/src/utils/frappeRequest.ts', import.meta.url)),
    },
  },
  build: {
    outDir: '../openlab_academy/public/espace',
    emptyOutDir: true,
    sourcemap: false,
    cssCodeSplit: false, // un seul espace.js et un seul espace.css, rechargés ensemble grâce à ?v=
    rollupOptions: {
      input: fileURLToPath(new URL('./src/main.js', import.meta.url)),
      output: { entryFileNames: 'espace.js', assetFileNames: 'espace[extname]', inlineDynamicImports: true },
    },
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.js'],
  },
})
