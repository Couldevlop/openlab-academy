<script setup lang="ts">
// Lots (Gradescope) : copies d'un même exercice auxquelles l'IA propose, avec assurance, les mêmes niveaux.
// Le formateur valide la proposition d'un geste, et peut publier dans la foulée ; tout ou rien côté serveur.
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { messageErreur } from '../../application/erreurs'
import type { FileCorrection } from '../../domaine/correction'
import { formaterNombre } from '../../domaine/grille'
import { lotsAffiches, type LotAffiche } from '../../domaine/lots'
import EnTete from '../composants/EnTete.vue'
import OngletsCorrection from '../composants/OngletsCorrection.vue'
import { utiliserCasUsages } from '../injection'
import { parametre } from '../routeur'

const cas = utiliserCasUsages()
const route = useRoute()
const file = ref<FileCorrection | null>(null)
const erreur = ref('')
const succes = ref('')
const occupe = ref(false)

const lots = computed(() => (file.value ? lotsAffiches(file.value) : []))

async function charger() {
  try {
    file.value = await cas.consulterFile.executer(parametre(route.query.exercice) || undefined)
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

onMounted(charger)

async function valider(lot: LotAffiche, etPublier: boolean) {
  if (occupe.value) return
  if (etPublier && !window.confirm(`Valider et publier les notes de ${lot.ids.length} copies ?`)) return
  occupe.value = true
  erreur.value = succes.value = ''
  try {
    const r = await cas.validerLot.executer(lot.ids, etPublier)
    succes.value = etPublier
      ? `${r.publiees.length} notes validées et publiées.`
      : `${r.copies.length} copies validées. Publiez-les depuis chaque copie.`
    await charger()
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    occupe.value = false
  }
}
</script>

<template>
  <div class="ecran">
    <EnTete>
      <OngletsCorrection :nb-lots="lots.length" />
    </EnTete>

    <main class="contenu">
      <h1>Validation par lots</h1>
      <p class="discret intro">
        Chaque lot réunit les copies d'un exercice auxquelles l'IA attribue, avec assurance, exactement les mêmes
        niveaux, sans écart avec les pairs ni correction déjà faite. Ouvrez une copie en cas de doute.
      </p>
      <p v-if="erreur" class="bandeau bandeau-erreur" role="alert">{{ erreur }}</p>
      <p v-if="succes" class="bandeau bandeau-info" role="status">{{ succes }}</p>
      <p v-if="file && !lots.length" class="vide">Aucun lot à valider pour le moment.</p>

      <section v-for="(lot, k) in lots" :key="lot.ids.join()" class="carte lot" :aria-labelledby="`lot-${k}`">
        <div class="lot-tete">
          <h2 :id="`lot-${k}`">Lot de {{ lot.ids.length }} copies</h2>
          <span class="discret">confiance IA ≥ {{ formaterNombre(lot.confiance) }}</span>
        </div>
        <p class="discret exercice">Exercice {{ lot.exercice }}</p>
        <ul>
          <li v-for="c in lot.copies" :key="c.copie">
            <RouterLink :to="{ name: 'correcteur', params: { copie: c.copie }, query: route.query }">
              Copie {{ c.copie }}
            </RouterLink>
            <span class="discret"> · version {{ c.version }}</span>
          </li>
        </ul>
        <div class="actions">
          <button type="button" class="bouton" :disabled="occupe" @click="valider(lot, false)">Valider le lot</button>
          <button type="button" class="bouton bouton-principal" :disabled="occupe" @click="valider(lot, true)">
            Valider et publier
          </button>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.contenu {
  max-width: 860px;
  margin: 0 auto;
  padding: 24px 16px 48px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
h1 {
  margin: 0;
  font-size: 26px;
}
.intro {
  margin: 0;
  max-width: 68ch;
}
.vide {
  font-family: var(--ol-font-display);
  font-size: 20px;
}
.lot {
  padding: 16px 18px;
}
.lot-tete {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
}
.lot-tete h2 {
  margin: 0;
  font-size: 18px;
}
.exercice {
  margin: 2px 0 8px;
  font-size: 13.5px;
}
ul {
  margin: 0 0 14px;
  padding-left: 18px;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.actions .bouton {
  flex: 1 1 160px;
}
@media (min-width: 768px) {
  .contenu {
    padding: 32px 32px 48px;
  }
}
</style>
