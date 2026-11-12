<script setup lang="ts">
// Fiche d'un dossier pour l'intendance : panneau latéral sur grand écran, feuille plein écran sur mobile. Identité,
// chiffres, échéancier, paiements, rappels par canal, journal (qui, quoi, quand, pourquoi) ; « Enregistrer un
// virement » et « Accorder un délai », motif obligatoire (ni l'un ni l'autre pour un dossier dispensé). Tout texte venu du serveur est rendu comme du texte.
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { messageErreur } from '../../application/erreurs'
import {
  detailAction,
  echeanceADecaler,
  etatEcheanceFiche,
  etatLigne,
  formaterHorodatage,
  isoHorodatage,
  libelleAction,
  validerDelai,
  validerVirement,
  type Erreurs,
  type EtatEcheanceFiche,
  type FicheIntendance,
  type SaisieDelai,
  type SaisieVirement,
} from '../../domaine/intendance'
import { formaterJour, formaterTelephone, formaterXof, libelleMode } from '../../domaine/paiement'
import { utiliserCasUsages } from '../injection'
import PuceStatut from './PuceStatut.vue'

const props = defineProps<{ dossier: string }>()
const emit = defineEmits<{ fermer: []; modifie: [] }>()

const ETATS: Record<EtatEcheanceFiche, string> = {
  dispensee: 'Dispensée',
  reglee: 'Réglée',
  en_retard: 'En retard',
  aujourdhui: 'Due aujourd’hui',
  a_venir: 'À venir',
}
const MOYENS = { cinetpay: 'CinetPay', virement: 'Virement' } as const
const STATUTS_PAIEMENT = { en_attente: 'En attente', confirme: 'Confirmé', echoue: 'Échoué' } as const
const CANAUX = { email: 'E-mail', sms: 'SMS', whatsapp: 'WhatsApp' } as const
const STATUTS_RAPPEL = { envoye: 'Envoyé', echec: 'Échec', ignore: 'Non envoyé (canal non configuré)' } as const

const cas = utiliserCasUsages()
const fiche = ref<FicheIntendance | null>(null)
const aujourdhui = ref('')
const chargement = ref(true)
const erreur = ref('')
const succes = ref('')
const formulaire = ref<'virement' | 'delai' | null>(null)
const envoi = ref(false)
const erreurServeur = ref('')

const virement = reactive<SaisieVirement>({ montant: '', reference: '', date: '', motif: '' })
const delai = reactive<SaisieDelai>({ jusquau: '', motif: '' })
const erreursVirement = ref<Erreurs<SaisieVirement>>({})
const erreursDelai = ref<Erreurs<SaisieDelai>>({})

const panneau = ref<HTMLElement | null>(null)
const titre = ref<HTMLElement | null>(null)
const messageSucces = ref<HTMLElement | null>(null)
let debordement = ''

const concernee = computed(() => (fiche.value ? echeanceADecaler(fiche.value) : null))
const delaiPossible = computed(() => !!fiche.value && !fiche.value.dispense && concernee.value !== null)
const demain = computed(() => {
  if (!aujourdhui.value) return ''
  const d = new Date(`${aujourdhui.value}T00:00:00Z`)
  d.setUTCDate(d.getUTCDate() + 1)
  return d.toISOString().slice(0, 10)
})

async function charger() {
  chargement.value = true
  erreur.value = ''
  try {
    const vue = await cas.ouvrirFiche.executer(props.dossier)
    fiche.value = vue.fiche
    aujourdhui.value = vue.aujourdhui
  } catch (e) {
    fiche.value = null
    erreur.value = messageErreur(e)
  } finally {
    chargement.value = false
  }
}

// clavier écouté sur le document : Échap et Tab restent pris en charge même si le focus a quitté le panneau
function surTouche(evenement: KeyboardEvent) {
  if (evenement.key === 'Escape') {
    evenement.preventDefault()
    fermer()
  } else if (evenement.key === 'Tab') garderLeFocus(evenement)
}

onMounted(async () => {
  document.addEventListener('keydown', surTouche)
  // la page derrière le voile ne défile plus tant que la fiche est ouverte
  debordement = document.documentElement.style.overflow
  document.documentElement.style.overflow = 'hidden'
  titre.value?.focus()
  await charger()
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', surTouche)
  document.documentElement.style.overflow = debordement
})

function fermer() {
  emit('fermer')
}

/** Le focus reste dans le panneau tant qu'il est ouvert ; hors de la liste (titre, message, page), il y revient. */
function garderLeFocus(evenement: KeyboardEvent) {
  const focusables = [
    ...(panneau.value?.querySelectorAll<HTMLElement>(
      'button:not([disabled]), a[href], input, select, textarea, [tabindex="0"]',
    ) ?? []),
  ]
  if (!focusables.length) return
  const premier = focusables[0]!
  const dernier = focusables[focusables.length - 1]!
  if (!focusables.includes(document.activeElement as HTMLElement)) {
    evenement.preventDefault()
    ;(evenement.shiftKey ? dernier : premier).focus()
  } else if (evenement.shiftKey && document.activeElement === premier) {
    evenement.preventDefault()
    dernier.focus()
  } else if (!evenement.shiftKey && document.activeElement === dernier) {
    evenement.preventDefault()
    premier.focus()
  }
}

async function ouvrir(quoi: 'virement' | 'delai') {
  succes.value = ''
  erreurServeur.value = ''
  formulaire.value = quoi
  if (quoi === 'virement') {
    Object.assign(virement, { montant: '', reference: '', date: aujourdhui.value, motif: '' })
    erreursVirement.value = {}
  } else {
    Object.assign(delai, { jusquau: '', motif: '' })
    erreursDelai.value = {}
  }
  await nextTick()
  panneau.value?.querySelector<HTMLElement>(`form.${quoi} input`)?.focus()
}

function annuler() {
  formulaire.value = null
  erreurServeur.value = ''
}

async function premierChampEnErreur(formulaireCss: string, erreurs: Partial<Record<string, string>>) {
  const champ = Object.keys(erreurs)[0]
  await nextTick()
  panneau.value?.querySelector<HTMLElement>(`form.${formulaireCss} [name="${champ}"]`)?.focus()
}

async function apresSucces(message: string) {
  formulaire.value = null
  succes.value = message
  emit('modifie')
  await charger()
  await nextTick()
  // le bouton qui avait le focus a disparu avec le formulaire : le message annonce le résultat et garde le focus
  messageSucces.value?.focus()
}

async function enregistrerVirement() {
  if (!fiche.value) return
  erreurServeur.value = ''
  erreursVirement.value = validerVirement(virement, aujourdhui.value)
  if (Object.keys(erreursVirement.value).length) return premierChampEnErreur('virement', erreursVirement.value)
  envoi.value = true
  try {
    await cas.enregistrerVirement.executer(fiche.value.dossier, { ...virement })
    await apresSucces('Virement enregistré.')
  } catch (e) {
    erreurServeur.value = messageErreur(e)
  } finally {
    envoi.value = false
  }
}

async function accorderDelai() {
  if (!fiche.value) return
  erreurServeur.value = ''
  erreursDelai.value = validerDelai(delai, aujourdhui.value)
  if (Object.keys(erreursDelai.value).length) return premierChampEnErreur('delai', erreursDelai.value)
  envoi.value = true
  try {
    await cas.accorderDelai.executer(fiche.value.dossier, { ...delai })
    await apresSucces('Délai enregistré.')
  } catch (e) {
    erreurServeur.value = messageErreur(e)
  } finally {
    envoi.value = false
  }
}

const decrit = (prefixe: string, champ: string, erreurs: Partial<Record<string, string>>) =>
  erreurs[champ] ? `${prefixe}-${champ}-erreur` : undefined
</script>

<template>
  <div class="voile" @click.self="fermer">
    <aside ref="panneau" class="fiche" role="dialog" aria-modal="true" aria-labelledby="fiche-titre">
      <header class="tete">
        <div class="tete-texte">
          <p class="surtitre">Fiche de paiement</p>
          <h2 id="fiche-titre" ref="titre" tabindex="-1">{{ fiche?.nom || 'Dossier' }}</h2>
        </div>
        <button type="button" class="fermer" aria-label="Fermer la fiche" @click="fermer">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18" /></svg>
        </button>
      </header>

      <div class="corps">
        <p v-if="chargement && !fiche" class="discret" role="status">Chargement de la fiche…</p>
        <p v-if="erreur" class="bandeau bandeau-erreur" role="alert">{{ erreur }}</p>

        <template v-if="fiche">
          <section class="identite" aria-label="Apprenant et parcours">
            <PuceStatut :etat="etatLigne(fiche)" />
            <dl>
              <div>
                <dt>E-mail</dt>
                <dd>{{ fiche.email }}</dd>
              </div>
              <div>
                <dt>Téléphone</dt>
                <dd>{{ fiche.telephone ? formaterTelephone(fiche.telephone) : 'Non renseigné' }}</dd>
              </div>
              <div>
                <dt>Parcours</dt>
                <dd>
                  {{ fiche.titre }}<span v-if="fiche.cohorte_titre" class="discret"> · {{ fiche.cohorte_titre }}</span>
                </dd>
              </div>
              <div>
                <dt>Mode</dt>
                <dd>{{ libelleMode(fiche.mode) }}</dd>
              </div>
              <div>
                <dt>Inscription</dt>
                <dd>{{ formaterJour(fiche.inscription) }}</dd>
              </div>
            </dl>
          </section>

          <section class="chiffres" aria-label="Montants">
            <div>
              <span class="petit">Payé</span>
              <strong>{{ formaterXof(fiche.paye) }}</strong>
              <span class="petit">sur {{ formaterXof(fiche.total) }}</span>
            </div>
            <div>
              <span class="petit">Reste dû</span>
              <strong>{{ formaterXof(fiche.reste) }}</strong>
            </div>
            <div :class="{ alerte: fiche.arriere > 0 }">
              <span class="petit">Arriéré</span>
              <strong>{{ formaterXof(fiche.arriere) }}</strong>
            </div>
          </section>
          <p v-if="fiche.dispense" class="bandeau bandeau-info">Dossier dispensé de paiement.</p>
          <p v-if="fiche.delai_jusqu_au" class="bandeau bandeau-info delai-en-cours">
            Délai accordé jusqu’au {{ formaterJour(fiche.delai_jusqu_au) }}.
          </p>

          <p v-if="succes" ref="messageSucces" class="succes" role="status" tabindex="-1">{{ succes }}</p>

          <div v-if="!formulaire && !fiche.dispense" class="actions">
            <button type="button" class="bouton bouton-principal vers-virement" @click="ouvrir('virement')">
              Enregistrer un virement
            </button>
            <button v-if="delaiPossible" type="button" class="bouton vers-delai" @click="ouvrir('delai')">
              Accorder un délai
            </button>
          </div>

          <form
            v-if="formulaire === 'virement'"
            class="saisie virement"
            novalidate
            @submit.prevent="enregistrerVirement"
          >
            <h3>Enregistrer un virement</h3>
            <div class="champ">
              <label for="virement-montant">Montant reçu (FCFA)</label>
              <input
                id="virement-montant"
                v-model="virement.montant"
                name="montant"
                type="text"
                inputmode="numeric"
                autocomplete="off"
                :aria-invalid="!!erreursVirement.montant"
                :aria-describedby="decrit('virement', 'montant', erreursVirement)"
              />
              <p v-if="erreursVirement.montant" id="virement-montant-erreur" class="erreur-champ">
                {{ erreursVirement.montant }}
              </p>
            </div>
            <div class="champ">
              <label for="virement-reference">Référence du virement</label>
              <input
                id="virement-reference"
                v-model="virement.reference"
                name="reference"
                type="text"
                maxlength="140"
                autocomplete="off"
                :aria-invalid="!!erreursVirement.reference"
                :aria-describedby="decrit('virement', 'reference', erreursVirement)"
              />
              <p v-if="erreursVirement.reference" id="virement-reference-erreur" class="erreur-champ">
                {{ erreursVirement.reference }}
              </p>
            </div>
            <div class="champ">
              <label for="virement-date">Date du virement</label>
              <input
                id="virement-date"
                v-model="virement.date"
                name="date"
                type="date"
                :max="aujourdhui"
                :aria-invalid="!!erreursVirement.date"
                :aria-describedby="decrit('virement', 'date', erreursVirement)"
              />
              <p v-if="erreursVirement.date" id="virement-date-erreur" class="erreur-champ">
                {{ erreursVirement.date }}
              </p>
            </div>
            <div class="champ">
              <label for="virement-motif">Motif (journalisé)</label>
              <input
                id="virement-motif"
                v-model="virement.motif"
                name="motif"
                type="text"
                maxlength="500"
                :aria-invalid="!!erreursVirement.motif"
                :aria-describedby="decrit('virement', 'motif', erreursVirement)"
              />
              <p v-if="erreursVirement.motif" id="virement-motif-erreur" class="erreur-champ">
                {{ erreursVirement.motif }}
              </p>
            </div>
            <p v-if="erreurServeur" class="bandeau bandeau-erreur" role="alert">{{ erreurServeur }}</p>
            <div class="boutons">
              <button type="submit" class="bouton bouton-principal" :disabled="envoi">
                {{ envoi ? 'Enregistrement…' : 'Enregistrer le virement' }}
              </button>
              <button type="button" class="bouton" @click="annuler">Annuler</button>
            </div>
          </form>

          <form v-if="formulaire === 'delai'" class="saisie delai" novalidate @submit.prevent="accorderDelai">
            <h3>Accorder un délai</h3>
            <p v-if="concernee" class="concernee">
              Échéance concernée : <strong>{{ formaterXof(concernee.montant) }}</strong> due le
              {{ formaterJour(concernee.date_limite) }}. L’accès au parcours reste ouvert jusqu’à la nouvelle date, qui
              couvre aussi les échéances tombant avant elle.
            </p>
            <div class="champ">
              <label for="delai-jusquau">Nouvelle date limite</label>
              <input
                id="delai-jusquau"
                v-model="delai.jusquau"
                name="jusquau"
                type="date"
                :min="demain"
                :aria-invalid="!!erreursDelai.jusquau"
                :aria-describedby="decrit('delai', 'jusquau', erreursDelai)"
              />
              <p v-if="erreursDelai.jusquau" id="delai-jusquau-erreur" class="erreur-champ">
                {{ erreursDelai.jusquau }}
              </p>
            </div>
            <div class="champ">
              <label for="delai-motif">Motif (journalisé)</label>
              <textarea
                id="delai-motif"
                v-model="delai.motif"
                name="motif"
                rows="3"
                maxlength="500"
                :aria-invalid="!!erreursDelai.motif"
                :aria-describedby="decrit('delai', 'motif', erreursDelai)"
              />
              <p v-if="erreursDelai.motif" id="delai-motif-erreur" class="erreur-champ">{{ erreursDelai.motif }}</p>
            </div>
            <p v-if="erreurServeur" class="bandeau bandeau-erreur" role="alert">{{ erreurServeur }}</p>
            <div class="boutons">
              <button type="submit" class="bouton bouton-principal" :disabled="envoi">
                {{ envoi ? 'Enregistrement…' : 'Accorder le délai' }}
              </button>
              <button type="button" class="bouton" @click="annuler">Annuler</button>
            </div>
          </form>

          <section class="bloc">
            <h3>Échéancier</h3>
            <ol class="echeancier">
              <li
                v-for="(e, i) in fiche.echeances"
                :key="i"
                :class="`etat-${etatEcheanceFiche(e, aujourdhui, fiche.dispense)}`"
              >
                <span class="date">{{ formaterJour(e.date_limite) }}</span>
                <span class="libelle">{{ e.libelle }}</span>
                <span class="montant">{{ formaterXof(e.montant) }}</span>
                <span class="etat">{{ ETATS[etatEcheanceFiche(e, aujourdhui, fiche.dispense)] }}</span>
              </li>
            </ol>
          </section>

          <section class="bloc paiements">
            <h3>Paiements</h3>
            <ul v-if="fiche.paiements.length">
              <li v-for="(p, i) in fiche.paiements" :key="i">
                <span class="ligne-un">
                  <strong>{{ MOYENS[p.moyen] }}</strong>
                  <span class="montant">{{ formaterXof(p.montant) }}</span>
                </span>
                <span class="discret">
                  Réf. {{ p.reference }} · {{ STATUTS_PAIEMENT[p.statut] }} ·
                  {{ formaterHorodatage(p.date_paiement || p.cree)
                  }}<template v-if="p.auteur"> · {{ p.auteur }}</template>
                </span>
              </li>
            </ul>
            <p v-else class="discret">Aucun paiement.</p>
          </section>

          <section class="bloc rappels">
            <h3>Rappels</h3>
            <ul v-if="fiche.rappels.length">
              <li v-for="(r, i) in fiche.rappels" :key="i">
                <span class="ligne-un">
                  <strong>{{ CANAUX[r.canal] }}</strong>
                  <span>{{ r.jours_avant }} {{ r.jours_avant > 1 ? 'jours' : 'jour' }} avant</span>
                </span>
                <span class="discret">
                  Échéance du {{ formaterJour(r.date_limite) }} · {{ STATUTS_RAPPEL[r.statut] }} ·
                  {{ formaterHorodatage(r.cree) }}
                </span>
              </li>
            </ul>
            <p v-else class="discret">Aucun rappel envoyé.</p>
          </section>

          <section class="bloc">
            <h3>Journal des actions</h3>
            <ol v-if="fiche.journal.length" class="journal">
              <li v-for="(j, i) in fiche.journal" :key="i">
                <span class="ligne-un">
                  <strong class="action">{{ libelleAction(j.action) }}</strong>
                  <time :datetime="isoHorodatage(j.horodatage)">{{ formaterHorodatage(j.horodatage) }}</time>
                </span>
                <span class="par"
                  >par <span class="acteur">{{ j.acteur }}</span></span
                >
                <ul v-if="detailAction(j).length" class="detail">
                  <li v-for="(d, k) in detailAction(j)" :key="k">{{ d }}</li>
                </ul>
                <p v-if="j.motif" class="motif">{{ j.motif }}</p>
              </li>
            </ol>
            <p v-else class="discret">Aucune action enregistrée.</p>
          </section>
        </template>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.voile {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  justify-content: flex-end;
  background: rgba(0, 19, 46, 0.45);
}
.fiche {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  background: var(--ol-ivory);
  box-shadow: -18px 0 40px rgba(0, 30, 72, 0.22);
  overflow: hidden;
}
@media (min-width: 768px) {
  .fiche {
    width: min(560px, 92vw);
    border-radius: 18px 0 0 18px;
  }
}
@media (prefers-reduced-motion: no-preference) {
  .fiche {
    animation: entree 180ms ease-out;
  }
  @keyframes entree {
    from {
      transform: translateX(24px);
      opacity: 0;
    }
  }
}
.tete {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px 16px 14px;
  background: var(--ol-navy);
  color: var(--es-sur-sombre);
  border-bottom: 4px solid transparent;
  border-image: var(--ol-filet) 1;
}
.tete-texte {
  flex: 1;
  min-width: 0;
}
.surtitre {
  margin: 0;
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  opacity: 0.85;
}
.tete h2 {
  margin: 2px 0 0;
  color: var(--es-sur-sombre);
  font-size: 21px;
  line-height: 1.25;
  overflow-wrap: anywhere;
}
.tete h2:focus-visible {
  outline-color: var(--ol-orange-light, #f39a5b);
}
.fermer {
  flex: none;
  width: 44px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 12px;
  background: transparent;
  color: var(--es-sur-sombre);
}
.fermer:hover {
  background: rgba(255, 255, 255, 0.12);
}
.fermer:focus-visible {
  outline-color: var(--ol-orange-light, #f39a5b);
}
.fermer svg {
  width: 20px;
  height: 20px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2.4;
  stroke-linecap: round;
}
.corps {
  flex: 1;
  overflow-y: auto;
  padding: 16px 16px 32px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.identite {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
}
dl {
  display: grid;
  grid-template-columns: 1fr;
  gap: 6px 16px;
  margin: 0;
  width: 100%;
}
@media (min-width: 480px) {
  dl {
    grid-template-columns: 1fr 1fr;
  }
}
dl div {
  min-width: 0;
}
dt {
  font-size: 12px;
  font-weight: 600;
  color: var(--es-gris);
}
dd {
  margin: 0;
  overflow-wrap: anywhere;
}
.chiffres {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 8px;
}
.chiffres > div {
  display: flex;
  flex-direction: column;
  padding: 10px 12px;
  border-radius: 12px;
  background: var(--es-surface);
  border: 1px solid var(--es-bord);
  min-width: 0;
}
.chiffres strong {
  font-family: var(--ol-font-display);
  font-size: 16px;
  color: var(--ol-navy);
}
.chiffres .alerte {
  border-color: var(--ol-orange);
}
.chiffres .alerte strong {
  color: #8a3300;
}
.petit {
  font-size: 12px;
  color: var(--es-gris);
}
.succes {
  margin: 0;
  padding: 10px 14px;
  border-radius: 10px;
  background: #dcf2e3;
  color: #14532d;
  font-weight: 600;
}
.actions,
.boutons {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.saisie {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  border-radius: 14px;
  background: var(--es-surface);
  border: 1px solid var(--es-bord-fort);
  border-top: 4px solid var(--ol-orange);
}
.saisie h3 {
  margin: 0;
  font-size: 17px;
}
.concernee {
  margin: 0;
  color: var(--es-encre);
}
.champ {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.champ label {
  font-weight: 600;
  font-size: 14px;
}
.champ input {
  min-height: 46px;
  padding: 8px 12px;
  border: 1px solid var(--es-bord-fort);
  border-radius: 10px;
  background: var(--es-surface);
  width: 100%;
}
.champ input[aria-invalid='true'] {
  border-color: var(--es-erreur);
}
.erreur-champ {
  margin: 0;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--es-erreur);
}
.bloc h3 {
  margin: 4px 0 8px;
  font-size: 15px;
  color: var(--ol-navy);
}
.bloc ul,
.bloc ol {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.bloc li {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--es-surface);
  border: 1px solid var(--es-bord);
  min-width: 0;
  overflow-wrap: anywhere;
}
.bloc p {
  margin: 0;
}
.ligne-un {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}
.echeancier li {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0 8px;
}
.echeancier .date {
  font-weight: 600;
}
.echeancier .montant {
  text-align: right;
  font-weight: 600;
}
.echeancier .etat {
  text-align: right;
  font-size: 13px;
  font-weight: 600;
}
.echeancier .libelle {
  color: var(--es-gris);
  font-size: 13.5px;
}
.etat-reglee .etat {
  color: #14532d;
}
.etat-en_retard {
  border-left: 4px solid var(--ol-orange);
}
.etat-en_retard .etat {
  color: #8a3300;
}
.etat-aujourdhui .etat,
.etat-a_venir .etat {
  color: var(--ol-navy-soft);
}
.journal > li {
  border-left: 4px solid var(--ol-navy-soft);
}
.bloc .detail {
  gap: 0;
  margin-top: 2px;
}
.bloc .detail li {
  padding: 0;
  border: 0;
  border-radius: 0;
  background: none;
  font-size: 14px;
  font-variant-numeric: tabular-nums;
}
.journal time,
.par {
  font-size: 13px;
  color: var(--es-gris);
}
.acteur {
  font-weight: 600;
  color: var(--es-encre);
}
.motif {
  margin-top: 4px;
  padding: 6px 10px;
  border-radius: 8px;
  background: var(--ol-ivory);
  white-space: pre-line;
}
</style>
