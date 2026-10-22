<script setup lang="ts">
// Correcteur (formateur, juré) : copie à gauche, grille à droite ; J/K copie suivante/précédente, 1–9 niveau du
// critère actif. La note se recalcule à chaque choix ; seule la publication la rend visible à l'apprenant.
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute, useRouter } from 'vue-router'
import { messageErreur } from '../../application/erreurs'
import {
  copieApresPublication,
  libelleStatut,
  niveauParTouche,
  propositionRetenue,
  saisieInitiale,
  type FileCorrection,
  type Saisie,
  type VueCopie,
} from '../../domaine/correction'
import { lienSur } from '../../domaine/dates'
import { calculerNote, complet, formaterNombre, reussie, type Niveaux } from '../../domaine/grille'
import CopieRendue from '../composants/CopieRendue.vue'
import EnTete from '../composants/EnTete.vue'
import GrilleCorrecteur from '../composants/GrilleCorrecteur.vue'
import OngletsCorrection from '../composants/OngletsCorrection.vue'
import { utiliserCasUsages } from '../injection'
import { parametre } from '../routeur'

const cas = utiliserCasUsages()
const route = useRoute()
const router = useRouter()

const file = ref<FileCorrection | null>(null)
const copie = ref<VueCopie | null>(null)
const niveaux = ref<Niveaux>({})
const commentaires = ref<Record<string, string>>({})
const general = ref('')
const actif = ref('')
const modifiee = ref(false)
const occupe = ref(false)
const erreur = ref('')
const succes = ref('')
const chargement = ref(true)

const id = computed(() => parametre(route.params.copie))
const exercice = computed(() => parametre(route.query.exercice) || undefined)
const copies = computed(() => file.value?.copies ?? [])
const rang = computed(() => copies.value.findIndex((c) => c.copie === id.value))
const nbLots = computed(() => file.value?.lots.length ?? 0)
const jure = computed(() => copie.value?.role === 'jury')
const grilleComplete = computed(() => !!copie.value && complet(copie.value.grille, niveaux.value))
const note = computed(() =>
  copie.value ? calculerNote(copie.value.grille, niveaux.value, copie.value.note_sur) : null,
)
const verdict = computed(() => (copie.value ? reussie(note.value, copie.value.seuil_reussite) : null))
const ia = computed(() => (copie.value ? propositionRetenue(copie.value) : null))
const citation = computed(() => ia.value?.citations[actif.value] ?? '')
const depot = computed(() => lienSur(copie.value?.source_url))
const saisie = (): Saisie => ({ niveaux: niveaux.value, commentaires: commentaires.value, general: general.value })

async function chargerFile() {
  file.value = await cas.consulterFile.executer(exercice.value)
}

function preparer(vue: VueCopie) {
  const depart = saisieInitiale(vue)
  niveaux.value = depart.niveaux
  commentaires.value = depart.commentaires
  general.value = depart.general
  actif.value = vue.grille.criteres[0]?.code ?? ''
  modifiee.value = false
}

async function chargerCopie() {
  erreur.value = ''
  if (!id.value) {
    copie.value = null
    const premiere = copies.value[0]
    if (premiere) void router.replace({ name: 'correcteur', params: { copie: premiere.copie }, query: route.query })
    return
  }
  try {
    const vue = await cas.ouvrirCopie.executer(id.value)
    copie.value = vue
    preparer(vue)
  } catch (e) {
    copie.value = null
    erreur.value = messageErreur(e)
  }
}

async function demarrer() {
  chargement.value = true
  try {
    await chargerFile()
  } catch (e) {
    erreur.value = messageErreur(e)
  }
  await chargerCopie()
  chargement.value = false
}

onMounted(demarrer)
watch(id, () => {
  succes.value = ''
  void chargerCopie()
})

// modifications non enregistrées : confirmation avant toute sortie (autre écran, autre copie, onglet, retour
// arrière du navigateur, fermeture ou rechargement de la page)
const abandonner = () => !modifiee.value || window.confirm('Quitter cette copie sans enregistrer vos choix ?')
onBeforeRouteLeave(() => abandonner())
onBeforeRouteUpdate((vers, depuis) => vers.params.copie === depuis.params.copie || abandonner())

function avantDechargement(evenement: BeforeUnloadEvent) {
  evenement.preventDefault()
  evenement.returnValue = ''
}
watch(modifiee, (sale) => {
  if (sale) window.addEventListener('beforeunload', avantDechargement)
  else window.removeEventListener('beforeunload', avantDechargement)
})
onBeforeUnmount(() => window.removeEventListener('beforeunload', avantDechargement))

function aller(decalage: number) {
  const cible = copies.value[rang.value + decalage]
  if (cible) void router.push({ name: 'correcteur', params: { copie: cible.copie }, query: route.query })
}

function surNiveaux(valeur: Niveaux) {
  niveaux.value = valeur
  modifiee.value = true
}

function surCommentaires(valeur: Record<string, string>) {
  commentaires.value = valeur
  modifiee.value = true
}

async function enregistrer() {
  if (!grilleComplete.value || occupe.value) return
  occupe.value = true
  erreur.value = succes.value = ''
  try {
    await cas.enregistrerCorrection.executer(id.value, saisie())
    modifiee.value = false
    succes.value = jure.value
      ? 'Votre note de juré est enregistrée.'
      : "Correction enregistrée. Elle n'est pas encore visible par l'apprenant."
    await chargerFile()
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    occupe.value = false
  }
}

async function publier() {
  if (!copie.value || !grilleComplete.value || occupe.value || jure.value) return
  const noteSur = copie.value.note_sur
  occupe.value = true
  erreur.value = succes.value = ''
  const suivante = copies.value[rang.value + 1]?.copie
  try {
    const publiee = await cas.publierNote.executer(id.value, saisie())
    modifiee.value = false // seulement une fois publiée : un échec garde la confirmation de sortie
    const message = `Note publiée : ${formaterNombre(publiee)} / ${noteSur}.`
    await chargerFile()
    const cible = copieApresPublication(
      copies.value.map((c) => c.copie),
      suivante,
      id.value,
    )
    if (cible) await router.push({ name: 'correcteur', params: { copie: cible }, query: route.query })
    else await chargerCopie()
    succes.value = message
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    occupe.value = false
  }
}

// raccourcis clavier : jamais pendant la saisie d'un commentaire, ni en touche maintenue (répétition) ou en cours
// de composition (méthode de saisie)
function clavier(evenement: KeyboardEvent) {
  const cible = evenement.target as HTMLElement | null
  if (evenement.ctrlKey || evenement.metaKey || evenement.altKey || evenement.repeat || evenement.isComposing) return
  if (cible?.closest?.('textarea, input, select, [contenteditable="true"]')) return
  const touche = evenement.key.toLowerCase()
  if (touche === 'j') aller(1)
  else if (touche === 'k') aller(-1)
  else if (/^[1-9]$/.test(touche) && copie.value) {
    const choix = niveauParTouche(copie.value.grille, actif.value, touche)
    if (!choix) return
    surNiveaux({ ...niveaux.value, [choix.code]: choix.indice })
    actif.value = choix.actif
  } else return
  evenement.preventDefault()
}

onMounted(() => window.addEventListener('keydown', clavier))
onBeforeUnmount(() => window.removeEventListener('keydown', clavier))
</script>

<template>
  <div class="ecran">
    <EnTete>
      <OngletsCorrection :nb-lots="nbLots" />
      <span class="espace" />
      <span v-if="rang >= 0" class="position">Copie {{ rang + 1 }} sur {{ copies.length }}</span>
      <div class="navigation">
        <button type="button" :disabled="rang <= 0" @click="aller(-1)">Précédente <kbd>K</kbd></button>
        <button type="button" :disabled="rang < 0 || rang >= copies.length - 1" @click="aller(1)">
          Suivante <kbd>J</kbd>
        </button>
      </div>
    </EnTete>

    <p v-if="chargement" class="etat discret" role="status">Chargement…</p>
    <div v-else-if="!copie" class="etat">
      <p v-if="erreur" class="bandeau bandeau-erreur" role="alert">{{ erreur }}</p>
      <p v-else-if="!copies.length" class="vide">Aucune copie à corriger pour le moment.</p>
    </div>

    <div v-else class="disposition">
      <main class="colonne-copie">
        <p class="surtitre discret">Version {{ copie.version }} · {{ libelleStatut(copie.statut) }}</p>
        <h1>{{ copie.titre }}</h1>

        <details v-if="copie.consigne" class="consigne carte">
          <summary>Consigne</summary>
          <CopieRendue :texte="copie.consigne" />
        </details>

        <p v-if="copie.signalement" class="bandeau bandeau-alerte signalement" role="alert">
          <strong>Attention :</strong> {{ copie.signalement }}. La pré-correction par l'IA est écartée pour cette copie
          : corrigez sur la seule copie.
        </p>

        <div class="bandeau bandeau-info contexte">
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="9" />
            <path d="M12 8v5M12 16h.01" />
          </svg>
          <div>
            <p>
              <template v-if="copie.controles.length"
                >Contrôles automatiques : {{ copie.controles.join(' ; ') }}.</template
              >
              <template v-else>Contrôles automatiques sans remarque.</template>
              <template v-if="copie.pairs.nombre">
                Relue par {{ copie.pairs.nombre }} pair{{ copie.pairs.nombre > 1 ? 's' : '' }}.</template
              >
              <template v-if="jure">
                Vous notez comme juré ({{ copie.jury.nombre }} note{{ copie.jury.nombre > 1 ? 's' : '' }} sur
                {{ copie.jury.attendus }}).</template
              >
            </p>
            <p v-if="copie.au_nom_de">Vous corrigez par délégation, au nom de {{ copie.au_nom_de }}.</p>
            <p v-if="depot">
              Dépôt : <a :href="depot" target="_blank" rel="noopener noreferrer nofollow">{{ depot }}</a>
              <template v-if="copie.commit"> · version {{ copie.commit }}</template>
            </p>
          </div>
        </div>

        <article class="carte texte-copie" aria-label="Copie de l'apprenant">
          <CopieRendue :texte="copie.contenu" :citation="citation" />
        </article>
      </main>

      <aside class="colonne-grille" aria-label="Grille d'évaluation">
        <div class="grille-tete">
          <h2>Grille</h2>
          <p class="note" aria-live="polite">
            {{ formaterNombre(note) }}<span> / {{ copie.note_sur }}</span>
          </p>
        </div>
        <p v-if="verdict !== null" class="verdict discret">
          {{ verdict ? 'Validé' : 'Non validé' }} au seuil de {{ formaterNombre(copie.seuil_reussite) }}
        </p>

        <GrilleCorrecteur
          v-model:actif="actif"
          :grille="copie.grille"
          :niveaux="niveaux"
          :commentaires="commentaires"
          :auto="copie.auto_evaluation"
          :ia="ia"
          :pairs="copie.pairs"
          :jury="copie.jury"
          @update:niveaux="surNiveaux"
          @update:commentaires="surCommentaires"
        />

        <div class="pied">
          <label for="commentaire-general">Commentaire pour l'apprenant</label>
          <textarea id="commentaire-general" v-model="general" rows="4" maxlength="5000" @input="modifiee = true" />
          <p v-if="erreur" class="bandeau bandeau-erreur" role="alert">{{ erreur }}</p>
          <p v-if="succes" class="bandeau bandeau-info" role="status">{{ succes }}</p>
          <div class="actions">
            <button type="button" class="bouton" :disabled="!grilleComplete || occupe" @click="enregistrer">
              {{ jure ? 'Enregistrer ma note' : 'Enregistrer' }}
            </button>
            <button
              v-if="!jure"
              type="button"
              class="bouton bouton-principal"
              :disabled="!grilleComplete || occupe"
              @click="publier"
            >
              Publier la note
            </button>
          </div>
          <p class="discret aide">
            <template v-if="!grilleComplete"
              >Choisissez un niveau pour chaque critère (touches 1 à {{ copie.grille.criteres[0]?.niveaux.length }}).
            </template>
            <template v-if="jure">Votre note rejoint la médiane du jury.</template>
            <template v-else>La note n'est visible par l'apprenant qu'après publication.</template>
          </p>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.ecran {
  min-height: 100vh;
}
.espace {
  flex-grow: 1;
}
.position {
  color: var(--es-entete-clair);
}
.navigation {
  display: flex;
  gap: 8px;
}
.navigation button {
  min-height: 40px;
  padding: 0 14px;
  border-radius: 8px;
  border: 1px solid var(--es-entete-bord);
  background: transparent;
  color: var(--es-entete-texte);
}
kbd {
  margin-left: 6px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--es-info);
  font-size: 12px;
}
.etat {
  padding: 32px 16px;
  max-width: 720px;
  margin: 0 auto;
}
.vide {
  font-family: var(--ol-font-display);
  font-size: 20px;
}

.disposition {
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  max-width: 1440px;
  margin: 0 auto;
}
.colonne-copie {
  flex: 999 1 560px;
  min-width: 0;
  padding: 24px 16px 40px;
}
.colonne-grille {
  flex: 1 1 460px;
  max-width: 100%;
  padding: 24px 16px 40px;
  background: var(--es-surface);
  border-top: 1px solid var(--es-bord);
}
.surtitre {
  margin: 0 0 4px;
}
h1 {
  margin: 0 0 20px;
  font-size: 24px;
  line-height: 1.2;
  font-weight: 700;
}
.consigne {
  margin-bottom: 20px;
  padding: 14px 18px;
}
.consigne :deep(.copie) {
  margin-top: 10px;
  max-width: 68ch;
  font-size: 15px;
}
.signalement,
.contexte {
  margin-bottom: 20px;
}
.signalement {
  display: block;
}
.contexte svg {
  flex: none;
  margin-top: 2px;
}
.contexte p + p {
  margin-top: 4px;
}
.contexte a {
  overflow-wrap: anywhere;
}
.texte-copie {
  max-width: 68ch;
  padding: 20px 18px;
}

.grille-tete {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}
.grille-tete h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
}
.note {
  margin: 0;
  font-family: var(--ol-font-display);
  font-size: 34px;
  font-weight: 700;
  color: var(--ol-navy);
}
.note span {
  font-size: 18px;
  color: var(--es-gris);
}
.verdict {
  margin: -4px 0 10px;
  font-size: 13px;
  text-align: right;
}
.pied {
  padding-top: 18px;
  border-top: 1px solid var(--es-bord);
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.pied label {
  font-weight: 600;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.actions .bouton {
  flex: 1 1 140px;
}
.actions .bouton-principal {
  flex: 2 1 180px;
}
.aide {
  margin: 0;
  font-size: 13px;
}

@media (min-width: 768px) {
  .colonne-copie {
    padding: 32px 40px 48px;
  }
  .colonne-grille {
    padding: 32px 32px 48px;
  }
  h1 {
    font-size: 30px;
  }
  .texte-copie {
    padding: 28px 32px;
  }
}
@media (min-width: 1100px) {
  .colonne-grille {
    max-width: 520px;
    border-top: none;
    border-left: 1px solid var(--es-bord);
  }
}
</style>
