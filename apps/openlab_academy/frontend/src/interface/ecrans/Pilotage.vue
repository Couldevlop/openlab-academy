<script setup lang="ts">
// Pilotage (super administrateur, responsable pédagogique) : tableau de bord des copies en souffrance (escalade
// épuisée : depuis quand, à qui, action prévue, temps restant) et réglages réellement appliqués à un exercice, avec
// l'origine de chaque valeur (défauts, type, YAML, surcharge) et l'équipe de correction. Le serveur vérifie le rôle.
import { computed, onMounted, ref } from 'vue'
import { messageErreur } from '../../application/erreurs'
import { formaterHorodatage, isoHorodatage } from '../../domaine/intendance'
import {
  formaterReste,
  libelleActionSouffrance,
  libelleTypeExercice,
  lignesEquipe,
  lignesReglages,
  type CopieEnSouffrance,
  type ReglagesEffectifs,
} from '../../domaine/pilotage'
import EnTete from '../composants/EnTete.vue'
import NavAgents from '../composants/NavAgents.vue'
import { utiliserCasUsages } from '../injection'

const cas = utiliserCasUsages()
const droits = cas.consulterDroits.executer()

const souffrances = ref<CopieEnSouffrance[] | null>(null)
const erreurSouffrances = ref('')

const exercice = ref('')
const cohorte = ref('')
const reglages = ref<ReglagesEffectifs | null>(null)
const examine = ref({ exercice: '', cohorte: '' })
const erreurReglages = ref('')
const occupe = ref(false)

const lignes = computed(() => (reglages.value ? lignesReglages(reglages.value) : []))
const equipe = computed(() => (reglages.value ? lignesEquipe(reglages.value.equipe) : []))

async function chargerSouffrances() {
  erreurSouffrances.value = ''
  try {
    souffrances.value = await cas.consulterSouffrances.executer()
  } catch (e) {
    erreurSouffrances.value = messageErreur(e)
  }
}

async function examiner() {
  if (occupe.value) return
  occupe.value = true
  erreurReglages.value = ''
  try {
    reglages.value = await cas.consulterReglagesEffectifs.executer(exercice.value, cohorte.value)
    examine.value = { exercice: exercice.value.trim(), cohorte: cohorte.value.trim() }
  } catch (e) {
    reglages.value = null
    erreurReglages.value = messageErreur(e)
  } finally {
    occupe.value = false
  }
}

/** Depuis une copie en souffrance : réglages de son exercice dans sa cohorte. */
function reglagesDe(c: CopieEnSouffrance) {
  exercice.value = c.exercice
  cohorte.value = c.cohorte
  void examiner()
  document.getElementById('titre-reglages')?.scrollIntoView?.({ behavior: 'smooth' })
}

onMounted(() => {
  if (droits.pilotage) void chargerSouffrances()
})
</script>

<template>
  <div class="ecran">
    <EnTete compact>
      <NavAgents :droits="droits" />
    </EnTete>
    <main class="contenu">
      <div>
        <p class="surtitre">Évaluation</p>
        <h1>Pilotage</h1>
      </div>

      <p v-if="!droits.pilotage" class="bandeau bandeau-info reserve">
        Cet écran est réservé au super administrateur et au responsable pédagogique.
      </p>

      <template v-else>
        <section class="carte bloc" aria-labelledby="titre-souffrances">
          <h2 id="titre-souffrances">Copies en souffrance</h2>
          <p class="discret intro">
            Copies dont l'escalade est épuisée : plus personne n'est relancé automatiquement. Ouvrez-les pour les
            corriger ou les réattribuer.
          </p>
          <p v-if="erreurSouffrances" class="bandeau bandeau-erreur" role="alert">{{ erreurSouffrances }}</p>
          <p v-else-if="!souffrances" class="discret" role="status">Chargement…</p>
          <p v-else-if="!souffrances.length" class="vide">Aucune copie en souffrance : la chaîne suit son cours.</p>
          <table v-else class="souffrances">
            <thead>
              <tr>
                <th scope="col">Copie</th>
                <th scope="col">Depuis</th>
                <th scope="col">Escaladée à</th>
                <th scope="col">Action prévue</th>
                <th scope="col"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in souffrances" :key="c.copie">
                <th scope="row" class="qui">
                  <RouterLink :to="{ name: 'correcteur', params: { copie: c.copie } }">Copie {{ c.copie }}</RouterLink>
                  <span class="discret"
                    >{{ c.apprenant }} · {{ c.exercice }}<template v-if="c.cohorte"> · {{ c.cohorte }}</template></span
                  >
                </th>
                <td data-label="Depuis">
                  <time :datetime="isoHorodatage(c.depuis)">{{ formaterHorodatage(c.depuis) || '—' }}</time>
                </td>
                <td data-label="Escaladée à" class="escalade">{{ c.escalade_a || '—' }}</td>
                <td data-label="Action prévue">
                  {{ libelleActionSouffrance(c.action) }}
                  <span v-if="c.reste_heures !== null" class="reste" :class="{ urgent: c.reste_heures <= 24 }">
                    {{ formaterReste(c.reste_heures) }}
                  </span>
                </td>
                <td class="geste">
                  <button type="button" class="bouton petit-bouton" @click="reglagesDe(c)">Réglages</button>
                </td>
              </tr>
            </tbody>
          </table>
        </section>

        <section class="carte bloc" aria-labelledby="titre-reglages">
          <h2 id="titre-reglages">Réglages appliqués</h2>
          <p class="discret intro">
            La chaîne réellement appliquée à un exercice, et l'origine de chaque valeur : défauts, type d'exercice, YAML
            de l'exercice ou surcharge de cohorte ou d'exercice.
          </p>
          <form class="recherche" @submit.prevent="examiner">
            <div class="champ">
              <label for="pilotage-exercice">Exercice</label>
              <input id="pilotage-exercice" v-model="exercice" type="text" autocomplete="off" required />
            </div>
            <div class="champ">
              <label for="pilotage-cohorte">Cohorte <span class="discret">(facultatif)</span></label>
              <input id="pilotage-cohorte" v-model="cohorte" type="text" autocomplete="off" />
            </div>
            <button type="submit" class="bouton bouton-principal" :disabled="occupe">Examiner</button>
          </form>
          <p v-if="erreurReglages" class="bandeau bandeau-erreur" role="alert">{{ erreurReglages }}</p>

          <template v-if="reglages">
            <p class="cible" role="status">
              {{ libelleTypeExercice(reglages.type_exercice) }} · exercice {{ examine.exercice
              }}<template v-if="examine.cohorte"> · cohorte {{ examine.cohorte }}</template>
            </p>
            <table class="reglages">
              <thead>
                <tr>
                  <th scope="col">Réglage</th>
                  <th scope="col">Valeur</th>
                  <th scope="col">Origine</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="l in lignes" :key="l.champ">
                  <th scope="row">{{ l.libelle }}</th>
                  <td data-label="Valeur">{{ l.valeur }}</td>
                  <td data-label="Origine">
                    <span class="origine">{{ l.source }}</span>
                  </td>
                </tr>
              </tbody>
            </table>

            <h3>Équipe de correction</h3>
            <table class="reglages equipe">
              <tbody>
                <tr v-for="l in equipe" :key="l.champ">
                  <th scope="row">{{ l.libelle }}</th>
                  <td data-label="Valeur">{{ l.valeur || '—' }}</td>
                  <td data-label="Origine">
                    <span v-if="l.source" class="origine">{{ l.source }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </template>
        </section>
      </template>
    </main>
  </div>
</template>

<style scoped>
.contenu {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px 16px 48px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.surtitre {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--es-gris);
}
h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
}
h2 {
  margin: 0 0 6px;
  font-size: 18px;
}
h3 {
  margin: 20px 0 8px;
  font-size: 15px;
}
.bloc {
  padding: 16px;
  min-width: 0;
}
.intro {
  margin: 0 0 12px;
  max-width: 72ch;
  font-size: 14px;
}
.vide {
  margin: 0;
  font-family: var(--ol-font-display);
  font-size: 18px;
}

/* tableaux : cartes sur mobile, tableau à partir de 760 px */
table {
  width: 100%;
  border-collapse: collapse;
}
thead {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
}
tr {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 0;
  border-bottom: 1px solid var(--es-bord);
}
tbody th {
  text-align: left;
  font-weight: 600;
}
td[data-label]::before {
  content: attr(data-label) ' : ';
  color: var(--es-gris);
  font-size: 13px;
}
.qui {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.qui .discret {
  font-weight: 400;
  font-size: 13px;
  overflow-wrap: anywhere;
}
.escalade {
  overflow-wrap: anywhere;
}
.reste {
  display: inline-block;
  margin-left: 6px;
  padding: 0 8px;
  border-radius: 9px;
  background: var(--es-info);
  color: var(--ol-navy);
  font-size: 13px;
  font-weight: 600;
}
.reste.urgent {
  background: var(--es-alerte-fond);
  color: var(--es-alerte-texte);
}
.petit-bouton {
  min-height: 36px;
  padding: 0 14px;
  font-size: 14px;
}

.recherche {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 10px 12px;
  margin-bottom: 12px;
}
.champ {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1 1 200px;
}
.champ label {
  font-weight: 600;
  font-size: 14px;
}
.champ input {
  min-height: 42px;
}
.cible {
  margin: 4px 0 8px;
  font-weight: 600;
  color: var(--ol-navy);
}
.origine {
  display: inline-block;
  padding: 0 8px;
  border-radius: 9px;
  background: var(--es-info);
  color: var(--ol-navy);
  font-size: 13px;
  font-weight: 600;
}

@media (min-width: 760px) {
  thead {
    position: static;
    width: auto;
    height: auto;
    overflow: visible;
    clip: auto;
  }
  tr {
    display: table-row;
    padding: 0;
  }
  th,
  td {
    padding: 10px 12px 10px 0;
    vertical-align: top;
    border-bottom: 1px solid var(--es-bord);
    text-align: left;
  }
  thead th {
    font-size: 13px;
    color: var(--es-gris);
    font-weight: 600;
  }
  td[data-label]::before {
    content: none;
  }
  .geste {
    text-align: right;
  }
  .equipe th {
    width: 34%;
  }
}
</style>
