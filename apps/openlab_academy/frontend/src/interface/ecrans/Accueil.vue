<script setup lang="ts">
import EnTete from '../composants/EnTete.vue'
import { utiliserCasUsages } from '../injection'

// liens des écrans d'agents selon les droits de la session ; l'API refuse elle-même tout rôle non habilité
const droits = utiliserCasUsages().consulterDroits.executer()
</script>

<template>
  <div class="ecran">
    <EnTete compact />
    <main class="contenu">
      <h1>Mon espace</h1>
      <RouterLink class="carte lien" :to="{ name: 'relecture' }">
        <strong>Mes relectures</strong>
        <span class="discret">Relire les copies de vos pairs et leur laisser un conseil.</span>
      </RouterLink>
      <RouterLink class="carte lien" :to="{ name: 'correcteur' }">
        <strong>Correction</strong>
        <span class="discret">Corriger et publier les copies qui vous sont confiées.</span>
      </RouterLink>
      <RouterLink v-if="droits.intendance" class="carte lien" :to="{ name: 'intendance' }">
        <strong>Intendance</strong>
        <span class="discret">Suivre les paiements, enregistrer un virement, accorder un délai.</span>
      </RouterLink>
      <RouterLink v-if="droits.finances" class="carte lien" :to="{ name: 'finances' }">
        <strong>Finances</strong>
        <span class="discret">Encaissements, recouvrement et retards, en résumé.</span>
      </RouterLink>
      <p class="discret">Vos retours de correction s'ouvrent depuis le lien laissé sur chaque exercice.</p>
    </main>
  </div>
</template>

<style scoped>
.contenu {
  max-width: 720px;
  margin: 0 auto;
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
h1 {
  margin: 0 0 8px;
  font-size: 26px;
}
.lien {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 16px;
  text-decoration: none;
  color: var(--es-encre);
}
.lien:hover {
  border-color: var(--ol-navy);
  color: var(--es-encre);
}
</style>
