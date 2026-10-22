<script setup lang="ts">
// Mes paiements (apprenant, mobile d'abord) : relevé du parcours (statut, prochain versement, part réglée), échéancier,
// choix du mode en trois cartes (groupe radio) avec téléphone, paiement en ligne ou virement. L'apprenant bloqué y
// arrive par la redirection du serveur. Les instructions de virement sont du texte brut, jamais du HTML.
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ErreurDepot, messageErreur } from '../../application/erreurs'
import {
  MODES,
  TELEPHONE_INVALIDE,
  calendrierMode,
  changement,
  enSouffrance,
  formaterJour,
  formaterTelephone,
  formaterXof,
  libelleMode,
  libelleStatut,
  lignesEcheancier,
  normaliserTelephone,
  progression,
  type DossierPaiement,
  type EtatEcheance,
  type Mode,
} from '../../domaine/paiement'
import EnTete from '../composants/EnTete.vue'
import { utiliserCasUsages } from '../injection'
import { parametre } from '../routeur'

const AUCUN_DOSSIER = 'Aucun dossier de paiement pour ce parcours. Vérifiez le lien ou contactez l’intendance.'
const ETATS: Record<EtatEcheance, string> = {
  reglee: 'Réglée',
  en_retard: 'En retard',
  aujourdhui: 'À régler aujourd’hui',
  a_venir: 'À venir',
}

const cas = utiliserCasUsages()
const route = useRoute()
const cours = computed(() => parametre(route.params.cours))

const dossier = ref<DossierPaiement | null>(null)
const aujourdhui = ref('')
const chargement = ref(true)
const erreur = ref('')

const mode = ref<Mode>('une_fois')
const telephone = ref('')
const telephoneTouche = ref(false)
const confirmation = ref(false)
const enregistrement = ref(false)
const erreurMode = ref('')
const succes = ref('')
const paiement = ref(false)
const erreurPaiement = ref('')

const titreConfirmation = ref<HTMLElement | null>(null)
const champTelephone = ref<HTMLInputElement | null>(null)
const boutonEnregistrer = ref<HTMLButtonElement | null>(null)

const lignes = computed(() => (dossier.value ? lignesEcheancier(dossier.value, aujourdhui.value) : []))
const part = computed(() => (dossier.value ? progression(dossier.value) : 0))
const modifiable = computed(() => dossier.value?.statut === 'a_jour' || dossier.value?.statut === 'en_retard')
// une échéance passée impayée : changer de mode l'effacerait, le serveur refuse (le téléphone reste modifiable)
const modesVerrouilles = computed(() => !!dossier.value && enSouffrance(dossier.value, aujourdhui.value))
const changeDeMode = computed(() => !!dossier.value && mode.value !== dossier.value.mode)
const telephoneChange = computed(
  () => !!dossier.value && (normaliserTelephone(telephone.value) ?? telephone.value) !== dossier.value.telephone,
)
const telephoneValide = computed(() => normaliserTelephone(telephone.value) !== null)
const telephoneEnErreur = computed(() => telephoneTouche.value && !telephoneValide.value)
const apresChangement = computed(() => (dossier.value ? changement(dossier.value, mode.value) : null))
const virementVisible = computed(
  () => !!dossier.value && (!dossier.value.paiement_en_ligne || dossier.value.instructions_virement !== ''),
)

function adopter(d: DossierPaiement) {
  dossier.value = d
  mode.value = d.mode
  telephone.value = formaterTelephone(d.telephone)
  telephoneTouche.value = false
}

async function charger() {
  chargement.value = true
  erreur.value = ''
  succes.value = ''
  confirmation.value = false
  try {
    const vue = await cas.chargerDossier.executer(cours.value)
    aujourdhui.value = vue.aujourdhui
    adopter(vue.dossier)
  } catch (e) {
    dossier.value = null
    erreur.value = e instanceof ErreurDepot && e.sorte === 'acces_refuse' ? AUCUN_DOSSIER : messageErreur(e)
  } finally {
    chargement.value = false
  }
}

/** Mode inchangé : téléphone seul, sans confirmation. Autre mode : confirmation d'abord. */
async function enregistrer() {
  succes.value = ''
  erreurMode.value = ''
  telephoneTouche.value = true
  if (!telephoneValide.value) {
    champTelephone.value?.focus()
    return
  }
  if (!changeDeMode.value) {
    await envoyer('Téléphone enregistré.')
    return
  }
  confirmation.value = true
  await nextTick()
  titreConfirmation.value?.focus()
}

async function annuler() {
  confirmation.value = false
  await nextTick()
  boutonEnregistrer.value?.focus()
}

async function envoyer(message: string | ((d: DossierPaiement) => string)) {
  enregistrement.value = true
  erreurMode.value = ''
  try {
    const d = await cas.choisirMode.executer(cours.value, mode.value, telephone.value)
    adopter(d)
    confirmation.value = false
    succes.value = typeof message === 'string' ? message : message(d)
  } catch (e) {
    erreurMode.value = messageErreur(e)
  } finally {
    enregistrement.value = false
  }
}

function confirmer() {
  return envoyer((d) =>
    d.statut === 'en_retard'
      ? 'Mode enregistré. Une échéance reste à régler.'
      : 'Mode enregistré : votre échéancier est à jour.',
  )
}

async function payer() {
  paiement.value = true
  erreurPaiement.value = ''
  try {
    await cas.payer.executer(cours.value)
  } catch (e) {
    erreurPaiement.value = messageErreur(e)
    paiement.value = false
  }
}

function libelleConfirmation(m: Mode) {
  return `Passer au paiement ${libelleMode(m).toLowerCase()} ?`
}

onMounted(charger)
watch(cours, charger)
</script>

<template>
  <div class="ecran">
    <EnTete compact>
      <a class="retour-parcours" href="/lms/courses">Mes parcours</a>
    </EnTete>
    <main class="contenu">
      <p v-if="chargement" class="discret" role="status">Chargement…</p>
      <template v-else-if="erreur">
        <h1 class="titre-seul">Mes paiements</h1>
        <p class="bandeau bandeau-erreur" role="alert">{{ erreur }}</p>
      </template>

      <template v-else-if="dossier">
        <div v-if="dossier.bloque" class="suspendu" role="note">
          <svg class="icone" viewBox="0 0 24 24" aria-hidden="true">
            <rect x="5" y="10.5" width="14" height="10" rx="2.5" />
            <path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5" />
          </svg>
          <p>
            <strong>L’accès à ce parcours est suspendu jusqu’au paiement de l’échéance en retard.</strong>
            Il se rouvre dès votre paiement confirmé. Vos autres parcours à jour restent ouverts.
          </p>
        </div>

        <section class="releve" :class="`releve-${dossier.statut}`" aria-labelledby="titre-paiement">
          <div class="releve-tete">
            <div>
              <h1 id="titre-paiement">Mes paiements</h1>
              <p class="parcours">{{ dossier.titre }}</p>
            </div>
            <p class="statut" :class="`statut-${dossier.statut}`">
              <svg class="icone" viewBox="0 0 24 24" aria-hidden="true">
                <path v-if="dossier.statut === 'en_retard'" d="M12 7v6M12 16.5v.5" />
                <path v-else d="M6.5 12.5l3.5 3.5 7.5-8" />
              </svg>
              <span>{{ libelleStatut(dossier.statut) }}</span>
            </p>
          </div>

          <div v-if="dossier.prochaine" class="prochain">
            <p class="prochain-libelle">Prochain versement</p>
            <p class="montant-prochain">{{ formaterXof(dossier.prochaine.montant) }}</p>
            <p v-if="dossier.prochaine.date_limite" class="echeance-prochaine">
              au plus tard le {{ formaterJour(dossier.prochaine.date_limite) }}
            </p>
            <button
              v-if="dossier.paiement_en_ligne"
              type="button"
              class="bouton bouton-principal payer"
              :disabled="paiement"
              :aria-busy="paiement"
              @click="payer"
            >
              {{ paiement ? 'Ouverture du paiement…' : `Payer ${formaterXof(dossier.prochaine.montant)}` }}
            </button>
            <p v-else class="bientot">
              Paiement en ligne bientôt disponible. En attendant, réglez par
              <a href="#virement">virement bancaire</a>.
            </p>
            <p v-if="erreurPaiement" class="erreur-releve" role="alert">{{ erreurPaiement }}</p>
            <p v-if="dossier.paiement_en_ligne" class="moyens">Orange Money, MTN, Moov, Wave ou carte bancaire</p>
          </div>
          <p v-else-if="dossier.statut === 'dispense'" class="fin">Vous êtes dispensé des frais de ce parcours.</p>
          <p v-else class="fin">Votre parcours est entièrement réglé. Merci !</p>

          <div class="avancement">
            <div
              class="jauge"
              role="progressbar"
              aria-label="Part du parcours réglée"
              aria-valuemin="0"
              aria-valuemax="100"
              :aria-valuenow="part"
              :aria-valuetext="`${formaterXof(dossier.paye)} réglés sur ${formaterXof(dossier.paye + dossier.reste)}`"
            >
              <span v-if="part > 0" :style="{ width: `${part}%`, backgroundSize: `${10000 / part}% 100%` }" />
            </div>
            <p>
              <strong>{{ formaterXof(dossier.paye) }}</strong> réglés sur
              {{ formaterXof(dossier.paye + dossier.reste) }}
            </p>
          </div>
        </section>

        <div class="colonnes">
          <section class="carte echeancier" aria-labelledby="titre-echeancier">
            <h2 id="titre-echeancier">Échéancier</h2>
            <ol>
              <li
                v-for="(l, i) in lignes"
                :key="`${l.date_limite}-${i}`"
                :class="[`etat-${l.etat}`, { 'est-prochaine': l.prochaine }]"
                :aria-current="l.prochaine ? 'step' : undefined"
              >
                <span class="repere" aria-hidden="true">
                  <svg v-if="l.etat === 'reglee'" viewBox="0 0 24 24"><path d="M6.5 12.5l3.5 3.5 7.5-8" /></svg>
                  <svg v-else-if="l.etat === 'en_retard' || l.etat === 'aujourdhui'" viewBox="0 0 24 24">
                    <path d="M12 7v6M12 16.5v.5" />
                  </svg>
                </span>
                <div class="ligne">
                  <p class="quand">{{ formaterJour(l.date_limite) }}</p>
                  <p class="quoi">{{ l.libelle }}</p>
                </div>
                <div class="ligne-droite">
                  <p class="montant">{{ formaterXof(l.montant) }}</p>
                  <p class="etat">{{ l.prochaine && l.etat === 'a_venir' ? 'Prochaine' : ETATS[l.etat] }}</p>
                </div>
              </li>
            </ol>
            <p v-if="!lignes.length" class="discret">Aucune échéance pour le moment.</p>
          </section>

          <section v-if="modifiable" class="carte modes" aria-labelledby="titre-modes">
            <h2 id="titre-modes">Mode de paiement</h2>
            <p class="discret aide-modes">
              Choisissez comment régler le parcours. Ce que vous avez déjà versé est conservé.
            </p>
            <p v-if="modesVerrouilles" id="modes-verrou" class="verrou">
              Réglez d’abord l’échéance en retard, ou contactez l’intendance, pour changer de mode.
            </p>
            <div
              class="choix"
              role="radiogroup"
              aria-labelledby="titre-modes"
              :aria-disabled="modesVerrouilles ? 'true' : undefined"
              :aria-describedby="modesVerrouilles ? 'modes-verrou' : undefined"
            >
              <label
                v-for="m in MODES"
                :key="m"
                class="mode"
                :class="{ choisi: mode === m, verrouille: modesVerrouilles }"
              >
                <input
                  v-model="mode"
                  class="sr-only"
                  type="radio"
                  name="mode"
                  :value="m"
                  :disabled="modesVerrouilles"
                />
                <span class="coche" aria-hidden="true">
                  <svg viewBox="0 0 24 24"><path d="M6.5 12.5l3.5 3.5 7.5-8" /></svg>
                </span>
                <span class="mode-corps">
                  <span class="mode-nom">{{ libelleMode(m) }}</span>
                  <span class="mode-prix">{{ formaterXof(dossier.tarif[m]) }}</span>
                  <span class="mode-calendrier">{{ calendrierMode(m) }}</span>
                  <span v-if="dossier.mode === m" class="actuel">Mode actuel</span>
                </span>
              </label>
            </div>
            <p class="discret frais">
              Prix global, frais d’inscription de {{ formaterXof(dossier.tarif.frais_inscription) }} compris.
            </p>

            <div class="champ">
              <label for="telephone">Téléphone Mobile Money</label>
              <input
                id="telephone"
                ref="champTelephone"
                v-model="telephone"
                type="tel"
                inputmode="tel"
                autocomplete="tel"
                placeholder="07 00 00 00 00"
                :aria-invalid="telephoneEnErreur ? 'true' : 'false'"
                :aria-describedby="telephoneEnErreur ? 'aide-telephone erreur-telephone' : 'aide-telephone'"
                @blur="telephoneTouche = telephoneTouche || telephone !== ''"
              />
              <p id="aide-telephone" class="discret aide">
                Pour vos rappels d’échéance par SMS et WhatsApp. 10 chiffres, +225 facultatif.
              </p>
              <p v-if="telephoneEnErreur" id="erreur-telephone" class="erreur-champ">{{ TELEPHONE_INVALIDE }}</p>
            </div>

            <div
              v-if="confirmation && apresChangement"
              class="confirmation"
              role="group"
              aria-labelledby="titre-confirmation"
            >
              <h3 id="titre-confirmation" ref="titreConfirmation" tabindex="-1">{{ libelleConfirmation(mode) }}</h3>
              <dl>
                <div>
                  <dt>Nouveau prix global</dt>
                  <dd>{{ formaterXof(apresChangement.total) }}</dd>
                </div>
                <div>
                  <dt>Déjà versé</dt>
                  <dd>{{ formaterXof(apresChangement.dejaVerse) }}</dd>
                </div>
                <div class="reste">
                  <dt>Reste à payer</dt>
                  <dd>{{ formaterXof(apresChangement.reste) }}</dd>
                </div>
              </dl>
              <p class="discret">Votre échéancier sera recalculé aussitôt, à partir de la prochaine échéance.</p>
              <div class="actions">
                <button
                  type="button"
                  class="bouton bouton-principal confirmer"
                  :disabled="enregistrement"
                  @click="confirmer"
                >
                  {{ enregistrement ? 'Enregistrement…' : 'Confirmer' }}
                </button>
                <button type="button" class="bouton annuler" :disabled="enregistrement" @click="annuler">
                  Annuler
                </button>
              </div>
            </div>
            <button
              v-else
              ref="boutonEnregistrer"
              type="button"
              class="bouton enregistrer"
              :disabled="enregistrement || (!changeDeMode && !telephoneChange)"
              @click="enregistrer"
            >
              {{ changeDeMode ? 'Enregistrer ce choix' : 'Enregistrer le téléphone' }}
            </button>
            <p v-if="erreurMode" class="bandeau bandeau-erreur" role="alert">{{ erreurMode }}</p>
            <p v-if="succes" class="succes" role="status">{{ succes }}</p>
          </section>
        </div>

        <section v-if="virementVisible" id="virement" class="carte virement" aria-labelledby="titre-virement">
          <h2 id="titre-virement">Payer par virement</h2>
          <p v-if="dossier.instructions_virement" class="instructions">{{ dossier.instructions_virement }}</p>
          <p v-else class="instructions">
            Les coordonnées de virement vous sont communiquées par l’intendance d’OpenLab Academy.
          </p>
          <p class="discret">
            Indiquez votre nom et le parcours dans le motif. Le virement est enregistré par l’intendance dès sa
            réception ; votre échéancier se met alors à jour.
          </p>
        </section>
      </template>
    </main>
  </div>
</template>

<style scoped>
.contenu {
  max-width: 1040px;
  margin: 0 auto;
  padding: 20px 16px 40px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.retour-parcours {
  margin-left: auto;
  font-weight: 600;
  font-size: 14px;
  color: var(--ol-navy);
}
.titre-seul {
  margin: 0;
  font-size: 26px;
}
.icone {
  width: 22px;
  height: 22px;
  flex: none;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

/* parcours suspendu : calme, bleu royal, jamais d'alarme rouge */
.suspendu {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 14px 16px;
  border-radius: 14px;
  background: var(--es-surface);
  border: 1px solid var(--es-bord-fort);
  border-left: 5px solid var(--ol-navy-soft);
  color: var(--es-encre);
}
.suspendu .icone {
  color: var(--ol-navy-soft);
  margin-top: 1px;
}
.suspendu p {
  margin: 0;
}
.suspendu strong {
  display: block;
  color: var(--ol-navy);
}

/* relevé : bleu nuit, filigrane de circuit imprimé du logo, filet quatre couleurs comme jauge */
.releve {
  position: relative;
  overflow: hidden;
  padding: 22px 20px 20px;
  border-radius: 18px;
  color: var(--es-sur-sombre);
  background-color: var(--ol-navy);
  background-image:
    radial-gradient(circle at 100% 0%, rgba(40, 144, 200, 0.28), transparent 55%),
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160' fill='none' stroke='%23ffffff' stroke-opacity='0.07' stroke-width='1.5'%3E%3Cpath d='M0 40h40l20 20h40M100 60l20-20h40M20 160v-50l20-20h30M120 160v-30l-20-20H80M60 0v20l20 20'/%3E%3Ccircle cx='100' cy='60' r='4'/%3E%3Ccircle cx='70' cy='90' r='4'/%3E%3Ccircle cx='80' cy='110' r='4'/%3E%3Ccircle cx='80' cy='40' r='3'/%3E%3C/svg%3E");
  background-size:
    auto,
    160px 160px;
  box-shadow: 0 18px 40px rgba(0, 30, 72, 0.22);
}
.releve-tete {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}
.releve h1 {
  margin: 0;
  color: var(--es-sur-sombre);
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.01em;
  opacity: 0.85;
}
.parcours {
  margin: 2px 0 0;
  font-family: var(--ol-font-display);
  font-size: 20px;
  line-height: 1.25;
  font-weight: 800;
}
.statut {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin: 0;
  padding: 4px 12px 4px 8px;
  border-radius: 999px;
  font-size: 13.5px;
  font-weight: 700;
  white-space: nowrap;
  background: var(--ol-mist);
  color: var(--ol-navy);
}
.statut .icone {
  width: 18px;
  height: 18px;
  stroke-width: 2.6;
}
.statut-a_jour {
  background: #dcf2e3;
  color: #14532d;
}
.statut-en_retard {
  background: #ffe6d4;
  color: #8a3300;
}
.statut-solde {
  background: var(--ol-sun);
  color: var(--ol-navy);
}
.prochain {
  margin-top: 22px;
}
.prochain p {
  margin: 0;
}
.prochain-libelle {
  font-size: 14px;
  opacity: 0.85;
}
.montant-prochain {
  font-family: var(--ol-font-display);
  font-size: clamp(38px, 11vw, 56px);
  line-height: 1.05;
  font-weight: 800;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
}
.echeance-prochaine {
  margin-top: 4px !important;
  font-size: 15px;
  color: var(--ol-sun);
  font-weight: 600;
}
.payer {
  margin-top: 18px;
  width: 100%;
  min-height: 54px;
  font-size: 17px;
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.28);
}
.releve :focus-visible {
  outline-color: var(--ol-sun);
}
.moyens {
  margin-top: 8px !important;
  font-size: 13px;
  opacity: 0.8;
  text-align: center;
}
.bientot {
  margin-top: 16px !important;
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px dashed rgba(255, 255, 255, 0.4);
  font-size: 14.5px;
}
.bientot a,
.bientot a:hover {
  color: var(--es-sur-sombre);
  font-weight: 700;
}
.erreur-releve {
  margin-top: 12px !important;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--es-alerte-fond);
  color: var(--es-erreur);
  font-weight: 600;
  font-size: 14px;
}
.fin {
  margin: 22px 0 0;
  font-family: var(--ol-font-display);
  font-size: 22px;
  font-weight: 700;
}
.avancement {
  margin-top: 22px;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.16);
}
.avancement p {
  margin: 8px 0 0;
  font-size: 14px;
  opacity: 0.9;
}
.avancement strong {
  opacity: 1;
}
.jauge {
  height: 10px;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.16);
  overflow: hidden;
}
.jauge span {
  display: block;
  height: 100%;
  min-width: 10px;
  border-radius: 5px;
  /* filet du logo déployé sur toute la jauge : la part réglée en révèle le début */
  background: var(--ol-filet, var(--ol-orange));
  background-repeat: no-repeat;
}

/* échéancier et modes */
.colonnes {
  display: grid;
  gap: 18px;
}
.carte {
  padding: 18px 16px;
}
.carte h2 {
  margin: 0 0 12px;
  font-size: 18px;
}
.echeancier ol {
  list-style: none;
  margin: 0;
  padding: 0;
}
.echeancier li {
  position: relative;
  display: grid;
  grid-template-columns: 26px 1fr auto;
  gap: 10px;
  align-items: start;
  padding: 10px 0 14px;
}
/* fil du calendrier entre les repères */
.echeancier li:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 12px;
  top: 34px;
  bottom: -8px;
  width: 2px;
  background: var(--es-bord-fort);
}
.echeancier li.etat-reglee:not(:last-child)::before {
  background: var(--ol-navy-soft);
}
.repere {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  border: 2px solid var(--es-bord-fort);
  background: var(--es-surface);
}
.repere svg {
  width: 16px;
  height: 16px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.etat-reglee .repere {
  border-color: var(--ol-navy-soft);
  background: var(--ol-navy-soft);
  color: var(--es-sur-sombre);
}
.etat-en_retard .repere,
.etat-aujourdhui .repere {
  border-color: var(--es-alerte-texte);
  background: var(--es-alerte-fond);
  color: var(--es-alerte-texte);
}
.est-prochaine .repere {
  border-color: var(--ol-orange);
  box-shadow: 0 0 0 4px rgba(236, 118, 35, 0.18);
}
.ligne p,
.ligne-droite p {
  margin: 0;
}
.quand {
  font-weight: 600;
  color: var(--ol-navy);
}
.quoi {
  font-size: 13.5px;
  color: var(--es-gris);
}
.ligne-droite {
  text-align: right;
}
.montant {
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}
.etat {
  display: inline-block;
  margin-top: 2px !important;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--es-gris);
}
.etat-reglee .etat {
  color: var(--ol-navy-soft);
}
.etat-en_retard .etat,
.etat-aujourdhui .etat {
  color: var(--es-alerte-texte);
}
.est-prochaine .etat {
  color: var(--ol-navy);
  padding: 0 8px;
  border-radius: 9px;
  background: var(--es-alerte-fond);
}
.etat-reglee .montant {
  color: var(--es-gris);
}

.aide-modes {
  margin: -6px 0 12px;
  font-size: 14px;
}
.choix {
  display: grid;
  gap: 10px;
}
.mode {
  position: relative;
  display: flex;
  gap: 12px;
  padding: 14px;
  border-radius: 14px;
  border: 1.5px solid var(--es-bord-fort);
  background: var(--es-surface);
  cursor: pointer;
}
.verrou {
  margin: 0 0 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--es-alerte-fond);
  color: var(--es-alerte-texte);
  font-size: 14px;
  font-weight: 600;
}
.mode.verrouille {
  cursor: not-allowed;
}
.mode.verrouille:not(.choisi) {
  background: var(--ol-ivory);
}
.mode:not(.verrouille):hover {
  border-color: var(--ol-navy-soft);
}
.mode.choisi {
  border: 2px solid var(--ol-navy);
  padding: 13.5px;
  box-shadow: inset 4px 0 0 var(--ol-orange);
}
.mode:has(input:focus-visible) {
  outline: 2px solid var(--ol-focus, #c25a12);
  outline-offset: 2px;
}
.coche {
  flex: none;
  width: 22px;
  height: 22px;
  margin-top: 2px;
  border-radius: 50%;
  border: 2px solid var(--es-gris);
  display: grid;
  place-items: center;
  color: transparent;
}
.coche svg {
  width: 14px;
  height: 14px;
  fill: none;
  stroke: currentColor;
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.choisi .coche {
  border-color: var(--ol-navy);
  background: var(--ol-navy);
  color: var(--es-sur-sombre);
}
.mode-corps {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.mode-nom {
  font-weight: 700;
  color: var(--ol-navy);
}
.mode-prix {
  font-family: var(--ol-font-display);
  font-size: 22px;
  font-weight: 800;
  color: var(--ol-navy);
  font-variant-numeric: tabular-nums;
}
.mode-calendrier {
  font-size: 13.5px;
  color: var(--es-gris);
}
.actuel {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 1px 8px;
  border-radius: 9px;
  font-size: 12px;
  font-weight: 700;
  background: var(--ol-mist);
  color: var(--ol-navy);
}
.frais {
  margin: 10px 0 16px;
  font-size: 13.5px;
}
.champ label {
  display: block;
  font-weight: 600;
  margin-bottom: 4px;
}
.champ input {
  width: 100%;
  min-height: 48px;
  padding: 10px 12px;
  border: 1.5px solid var(--es-bord-fort);
  border-radius: 10px;
  background: var(--es-surface);
  font-size: 16px;
  font-variant-numeric: tabular-nums;
}
.champ input::placeholder {
  color: var(--ol-slate, #6b7590);
}
.champ input:focus-visible {
  border-color: var(--ol-navy);
}
.champ input[aria-invalid='true'] {
  border-color: var(--es-erreur);
}
.aide {
  margin: 4px 0 0;
  font-size: 13px;
}
.erreur-champ {
  margin: 4px 0 0;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--es-erreur);
}
.enregistrer {
  margin-top: 16px;
  width: 100%;
}
.confirmation {
  margin-top: 16px;
  padding: 16px;
  border-radius: 14px;
  background: var(--ol-ivory);
  border: 1.5px solid var(--ol-navy);
}
.confirmation h3 {
  margin: 0 0 10px;
  font-size: 16px;
  color: var(--ol-navy);
}
.confirmation dl {
  margin: 0 0 8px;
}
.confirmation dl div {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 4px 0;
}
.confirmation dt {
  color: var(--es-gris);
}
.confirmation dd {
  margin: 0;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.confirmation .reste {
  border-top: 1px solid var(--es-bord-fort);
  margin-top: 4px;
  padding-top: 8px;
}
.confirmation .reste dt,
.confirmation .reste dd {
  color: var(--ol-navy);
  font-weight: 800;
}
.confirmation > p {
  margin: 0 0 12px;
  font-size: 13.5px;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.actions .bouton {
  flex: 1 1 140px;
}
.modes .bandeau-erreur {
  margin-top: 12px;
}
.succes {
  margin: 12px 0 0;
  padding: 10px 12px;
  border-radius: 10px;
  background: #e6f4ea;
  color: var(--es-succes);
  font-weight: 600;
}

.virement {
  border-top: 4px solid var(--ol-sky);
  scroll-margin-top: 16px;
}
.instructions {
  margin: 0 0 10px;
  padding: 12px 14px;
  border-radius: 10px;
  background: var(--ol-ivory);
  white-space: pre-line;
  overflow-wrap: anywhere;
  font-weight: 500;
}
.virement .discret {
  margin: 0;
  font-size: 13.5px;
}

@media (min-width: 900px) {
  .contenu {
    padding: 32px 24px 56px;
    gap: 22px;
  }
  .releve {
    padding: 30px 34px 26px;
    display: grid;
    grid-template-columns: 1.3fr 1fr;
    column-gap: 40px;
  }
  .releve-tete {
    grid-column: 1 / -1;
  }
  .parcours {
    font-size: 26px;
  }
  .prochain,
  .fin {
    grid-column: 1;
  }
  .avancement {
    grid-column: 2;
    grid-row: 2;
    align-self: end;
    border-top: none;
    padding-top: 0;
  }
  .colonnes {
    grid-template-columns: 1.1fr 1fr;
    align-items: start;
  }
  .carte {
    padding: 22px 24px;
  }
  .payer {
    width: auto;
    min-width: 280px;
  }
  .moyens {
    text-align: left;
  }
}

@media (prefers-reduced-motion: no-preference) {
  .jauge span {
    animation: remplir 900ms cubic-bezier(0.2, 0.7, 0.2, 1) both;
    transform-origin: left center;
  }
  .mode,
  .coche {
    transition:
      border-color 120ms ease,
      background-color 120ms ease;
  }
}
@keyframes remplir {
  from {
    transform: scaleX(0);
  }
}
</style>
