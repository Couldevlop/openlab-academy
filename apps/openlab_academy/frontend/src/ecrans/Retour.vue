<script setup>
// Mon retour (apprenant, mobile d'abord) : note, niveau et commentaire par critère, mention « provisoire ».
// Tant que l'apprenant doit des relectures, la note reste en attente. Les commentaires sont du texte brut.
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import EnTete from '../composants/EnTete.vue'
import { lire, messageErreur } from '../lib/api'
import { formaterNombre } from '../lib/grille'

const route = useRoute()
const retour = ref(null)
const erreur = ref('')
const chargement = ref(true)

const visible = computed(() => retour.value && !retour.value.masquee && retour.value.criteres.length > 0)
const remarquesPairs = computed(() => [...new Set((retour.value?.criteres || []).flatMap((c) => c.pairs))])

function segments(c) {
  const dernier = c.niveaux.length - 1
  return c.niveaux.map((_, i) => (c.niveau === null || i > c.niveau ? 'vide' : i === dernier ? 'sommet' : 'atteint'))
}

async function charger() {
  chargement.value = true
  erreur.value = ''
  try {
    retour.value = await lire('mon_retour', { copie: route.params.copie })
  } catch (e) {
    retour.value = null
    erreur.value = messageErreur(e)
  } finally {
    chargement.value = false
  }
}

onMounted(charger)
watch(() => route.params.copie, charger)
</script>

<template>
  <div class="ecran">
    <EnTete compact />
    <main class="contenu">
      <p v-if="chargement" class="discret" role="status">Chargement…</p>
      <p v-else-if="erreur" class="bandeau bandeau-erreur" role="alert">{{ erreur }}</p>

      <template v-else-if="retour">
        <div>
          <p class="surtitre discret">
            Mon retour<template v-if="retour.provisoire"> · <span class="provisoire">provisoire</span></template>
          </p>
          <h1>{{ retour.titre }}</h1>

          <div v-if="retour.masquee" class="carte attente">
            <h2>Note en attente</h2>
            <p>{{ retour.message }}</p>
            <RouterLink class="bouton bouton-principal" :to="{ name: 'relecture' }">Faire mes relectures</RouterLink>
          </div>

          <p v-else-if="retour.note === null" class="bandeau bandeau-info" role="status">{{ retour.message }}</p>

          <div v-else class="note">
            <p class="valeur">{{ formaterNombre(retour.note) }}</p>
            <div class="sur">
              <p class="discret">sur {{ retour.note_sur }}</p>
              <p v-if="retour.reussite === true" class="reussi">Validé</p>
              <p v-else-if="retour.reussite === false" class="non-valide">Non validé</p>
            </div>
          </div>
          <p v-if="retour.provisoire && retour.note !== null" class="bandeau bandeau-alerte mention" role="note">
            {{ retour.message }}
          </p>
        </div>

        <blockquote v-if="visible && retour.commentaire_general" class="carte general">
          <p>{{ retour.commentaire_general }}</p>
        </blockquote>

        <section v-if="visible" aria-label="Détail par critère" class="criteres">
          <div v-for="c in retour.criteres" :key="c.code" class="carte critere">
            <div class="critere-tete">
              <h2>{{ c.libelle }}</h2>
              <span>{{ c.niveau_libelle || '–' }}</span>
            </div>
            <div class="barre" aria-hidden="true" :style="{ gridTemplateColumns: `repeat(${c.niveaux.length}, minmax(0, 1fr))` }">
              <span v-for="(etat, i) in segments(c)" :key="i" :class="etat" />
            </div>
            <p v-if="c.auto_evaluation !== null || c.commentaire" class="discret detail">
              <template v-if="c.auto_evaluation !== null">Votre auto-évaluation : {{ c.niveaux[c.auto_evaluation] }}.</template>
              {{ c.commentaire }}
            </p>
          </div>
        </section>

        <section v-if="visible && remarquesPairs.length" class="pairs">
          <h2>Ce que vos pairs ont retenu</h2>
          <p v-for="(r, i) in remarquesPairs" :key="i">« {{ r }} »</p>
        </section>
      </template>
    </main>
  </div>
</template>

<style scoped>
.contenu { max-width: 720px; margin: 0 auto; padding: 24px 16px 28px; display: flex; flex-direction: column; gap: 18px; }
.surtitre { margin: 0 0 2px; font-size: 13.5px; }
.provisoire {
  display: inline-block; padding: 0 8px; border-radius: 9px; background: var(--es-alerte-fond);
  color: var(--es-alerte-texte); font-weight: 600;
}
h1 { margin: 0 0 14px; font-size: 23px; line-height: 1.2; font-weight: 700; }
.note { display: flex; align-items: flex-end; gap: 12px; }
.valeur { margin: 0; font-family: var(--ol-font-display); font-size: 64px; line-height: 0.9; font-weight: 700; color: var(--ol-navy); }
.sur { padding-bottom: 4px; }
.sur p { margin: 0; }
.reussi { font-weight: 600; color: var(--es-succes); }
.non-valide { font-weight: 600; color: var(--es-alerte-texte); }
.mention { margin-top: 14px; }
.attente { padding: 16px; display: flex; flex-direction: column; gap: 10px; align-items: flex-start; }
.attente h2 { margin: 0; font-size: 18px; }
.attente p { margin: 0; }
.general { margin: 0; padding: 14px 16px; }
.general p { margin: 0; white-space: pre-line; overflow-wrap: anywhere; }
.criteres { display: flex; flex-direction: column; gap: 10px; }
.critere { padding: 14px 16px; }
.critere-tete { display: flex; justify-content: space-between; gap: 8px; margin-bottom: 8px; }
.critere-tete h2 { margin: 0; font-family: var(--ol-font-body); font-size: 15px; font-weight: 600; }
.critere-tete span { font-size: 14px; font-weight: 600; text-align: right; }
.barre { display: grid; gap: 4px; }
.barre span { height: 6px; border-radius: 3px; background: var(--es-bord); }
.barre .atteint { background: var(--ol-navy); }
.barre .sommet { background: var(--ol-orange); }
.detail { margin: 8px 0 0; font-size: 13.5px; white-space: pre-line; overflow-wrap: anywhere; }
.pairs { padding: 14px 16px; background: var(--es-info); border-radius: 12px; }
.pairs h2 { margin: 0 0 6px; font-family: var(--ol-font-body); font-size: 15px; font-weight: 600; }
.pairs p { margin: 0 0 6px; font-size: 14px; white-space: pre-line; overflow-wrap: anywhere; }
.pairs p:last-child { margin: 0; }
</style>
