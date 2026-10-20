<script setup>
// Lots (Gradescope) : copies d'un même exercice auxquelles l'IA propose, avec assurance, les mêmes niveaux.
// Le formateur valide la proposition d'un geste, et peut publier dans la foulée ; tout ou rien côté serveur.
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import EnTete from '../composants/EnTete.vue'
import { ecrire, lire, messageErreur } from '../lib/api'
import { formaterNombre } from '../lib/grille'

const route = useRoute()
const file = ref(null)
const erreur = ref('')
const succes = ref('')
const occupe = ref(false)

const parCopie = computed(() => Object.fromEntries((file.value?.copies || []).map((c) => [c.copie, c])))
const lots = computed(() =>
  (file.value?.lots || []).map((ids) => {
    const copies = ids.map((id) => parCopie.value[id] || { copie: id })
    return { ids, copies, exercice: copies[0]?.exercice || '', confiance: Math.min(...copies.map((c) => c.confiance ?? 1)) }
  }),
)

async function charger() {
  try {
    file.value = await lire('file_correction', route.query.exercice ? { exercice: route.query.exercice } : {})
  } catch (e) {
    erreur.value = messageErreur(e)
  }
}

onMounted(charger)

async function valider(lot, etPublier) {
  if (occupe.value) return
  if (etPublier && !window.confirm(`Valider et publier les notes de ${lot.ids.length} copies ?`)) return
  occupe.value = true
  erreur.value = succes.value = ''
  try {
    const r = await ecrire('valider_lot', { copies: lot.ids, et_publier: etPublier ? 1 : 0 })
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
      <nav class="onglets" aria-label="Correction">
        <RouterLink :to="{ name: 'correcteur', query: route.query }">À corriger</RouterLink>
        <RouterLink :to="{ name: 'lots', query: route.query }">Lots<template v-if="lots.length"> ({{ lots.length }})</template></RouterLink>
      </nav>
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
.onglets { display: flex; gap: 16px; }
.onglets a { color: var(--es-entete-doux); text-decoration: none; }
.onglets a.router-link-active { color: #fff; text-decoration: underline; text-underline-offset: 6px; }
.contenu { max-width: 860px; margin: 0 auto; padding: 24px 16px 48px; display: flex; flex-direction: column; gap: 16px; }
h1 { margin: 0; font-size: 26px; }
.intro { margin: 0; max-width: 68ch; }
.vide { font-family: var(--ol-font-display); font-size: 20px; }
.lot { padding: 16px 18px; }
.lot-tete { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: baseline; gap: 8px; }
.lot-tete h2 { margin: 0; font-size: 18px; }
.exercice { margin: 2px 0 8px; font-size: 13.5px; }
ul { margin: 0 0 14px; padding-left: 18px; }
.actions { display: flex; flex-wrap: wrap; gap: 10px; }
.actions .bouton { flex: 1 1 160px; }
@media (min-width: 768px) {
  .contenu { padding: 32px 32px 48px; }
}
</style>
