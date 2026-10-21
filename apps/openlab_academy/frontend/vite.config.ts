import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

// Seuils de couverture : le cœur (domaine, cas d'usage, adaptateurs) entièrement couvert, comme le back ; les écrans
// à 90 % au moins.
const TOUT = { lines: 100, branches: 100, functions: 100, statements: 100 }
const ECRANS = { lines: 90, branches: 90, functions: 90, statements: 90 }

// Paquet servi par Frappe sous /assets/openlab_academy/espace/ ; noms fixes, la page www/espace.html les charge.
export default defineConfig({
  plugins: [vue()],
  base: '/assets/openlab_academy/espace/',
  resolve: {
    alias: {
      // seule la requête Frappe de frappe-ui (jeton CSRF, erreurs) : ses composants ne sont pas embarqués
      'frappe-ui-requete': fileURLToPath(
        new URL('./node_modules/frappe-ui/src/utils/frappeRequest.ts', import.meta.url),
      ),
    },
  },
  build: {
    outDir: '../openlab_academy/public/espace',
    emptyOutDir: true,
    sourcemap: false,
    cssCodeSplit: false, // un seul espace.js et un seul espace.css, rechargés ensemble grâce à ?v=
    rollupOptions: {
      input: fileURLToPath(new URL('./src/main.ts', import.meta.url)),
      output: { entryFileNames: 'espace.js', assetFileNames: 'espace[extname]', inlineDynamicImports: true },
      // annotations /* @__PURE__ */ mal placées dans zod : sans effet sur le paquet, avertissement écarté
      onwarn(avertissement, suite) {
        if (avertissement.code === 'INVALID_ANNOTATION' && avertissement.id?.includes('node_modules/zod/')) return
        suite(avertissement)
      },
    },
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,vue}'],
      // point d'entrée (trois lignes de branchement, exercé sur le banc), déclarations et aides de test
      exclude: ['src/main.ts', 'src/**/*.d.ts', 'src/**/*.test.ts', 'src/test/**'],
      reporter: ['text', 'text-summary'],
      thresholds: {
        'src/domaine/**': TOUT,
        'src/application/**': TOUT,
        'src/infrastructure/**': TOUT,
        'src/interface/**': ECRANS,
      },
    },
  },
})
