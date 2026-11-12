<script setup lang="ts">
// Onglets du correcteur : copies à corriger et lots, en gardant le filtre (exercice) de l'adresse.
import { useRoute } from 'vue-router'

defineProps<{ nbLots: number }>()
const route = useRoute()
</script>

<template>
  <nav class="onglets" aria-label="Correction">
    <RouterLink :to="{ name: 'accueil' }" class="espace">Mon espace</RouterLink>
    <RouterLink :to="{ name: 'correcteur', query: route.query }">À corriger</RouterLink>
    <RouterLink :to="{ name: 'lots', query: route.query }"
      >Lots<template v-if="nbLots"> ({{ nbLots }})</template></RouterLink
    >
  </nav>
</template>

<style scoped>
.onglets .espace {
  margin-right: 8px;
}
.onglets {
  display: flex;
  gap: 16px;
}
.onglets a {
  color: var(--es-entete-doux);
  text-decoration: none;
}
.onglets a.router-link-active {
  color: var(--es-entete-texte);
  font-weight: 600;
  text-decoration: underline;
  text-decoration-color: var(--ol-orange);
  text-decoration-thickness: 2px;
  text-underline-offset: 6px;
}
</style>
