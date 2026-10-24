<script setup lang="ts">
// Liens entre les écrans des agents, selon les droits de la session (l'API refuse elle-même tout rôle non habilité).
import type { Droits } from '../../application/ports'

defineProps<{ droits: Droits }>()
</script>

<template>
  <nav class="nav-agents" aria-label="Écrans de gestion">
    <RouterLink :to="{ name: 'accueil' }">Mon espace</RouterLink>
    <RouterLink v-if="droits.intendance" :to="{ name: 'intendance' }">Intendance</RouterLink>
    <RouterLink v-if="droits.finances" :to="{ name: 'finances' }">Finances</RouterLink>
    <RouterLink v-if="droits.pilotage" :to="{ name: 'pilotage' }">Pilotage</RouterLink>
  </nav>
</template>

<style scoped>
.nav-agents {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-left: auto;
}
.nav-agents a {
  display: inline-flex;
  align-items: center;
  min-height: 40px;
  padding: 0 12px;
  border-radius: 999px;
  font-weight: 600;
  font-size: 14px;
  color: var(--ol-navy);
  text-decoration: none;
}
.nav-agents a:hover {
  background: var(--es-info);
}
.nav-agents a.router-link-exact-active {
  background: var(--ol-navy);
  color: var(--es-sur-sombre);
}
</style>
