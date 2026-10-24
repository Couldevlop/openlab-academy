<script setup lang="ts">
// Intendance (intendant, administrateur) : filtres, export Excel, indicateurs en cartes, dossiers en tableau trié
// (cartes sur mobile), fiche en panneau latéral avec virement et délai. Statut et blocage viennent du serveur.
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { messageErreur } from '../../application/erreurs'
import {
  FILTRES_VIDES,
  etatLigne,
  libelleEtat,
  trier,
  type CleTri,
  type Filtres,
  type LigneIntendance,
  type Sens,
  type VueIntendance,
} from '../../domaine/intendance'
import {
  MODES,
  formaterJour,
  formaterXof,
  libelleMode,
  libelleStatut,
  type StatutPaiement,
} from '../../domaine/paiement'
import EnTete from '../composants/EnTete.vue'
import FichePaiement from '../composants/FichePaiement.vue'
import Indicateur from '../composants/Indicateur.vue'
import NavAgents from '../composants/NavAgents.vue'
import PuceStatut from '../composants/PuceStatut.vue'
import { utiliserCasUsages } from '../injection'

// statuts du domaine, plus « Bloqué » (arriéré sans délai) : tous filtrés par le serveur, vue et export
const STATUTS: { valeur: Filtres['statut']; libelle: string }[] = [
  ...(['a_jour', 'en_retard', 'solde', 'dispense'] as StatutPaiement[]).map((s) => ({
    valeur: s,
    libelle: libelleStatut(s),
  })),
  { valeur: 'bloque', libelle: libelleEtat('bloque') },
]
const COLONNES: { cle: CleTri; libelle: string }[] = [
  { cle: 'nom', libelle: 'Apprenant' },
  { cle: 'parcours', libelle: 'Parcours' },
  { cle: 'paye', libelle: 'Payé / total' },
  { cle: 'prochaine', libelle: 'Prochaine échéance' },
  { cle: 'etat', libelle: 'Statut' },
]
const TRIS_MOBILE: { valeur: string; libelle: string }[] = [
  { valeur: '', libelle: 'Ordre d’inscription' },
  { valeur: 'etat:asc', libelle: 'Urgence' },
  { valeur: 'prochaine:asc', libelle: 'Prochaine échéance' },
  { valeur: 'reste:desc', libelle: 'Reste dû' },
  { valeur: 'nom:asc', libelle: 'Nom' },
]

const cas = utiliserCasUsages()
const droits = cas.consulterDroits.executer()

const filtres = reactive<Filtres>({ ...FILTRES_VIDES })
const appliques = ref<Filtres>({ ...FILTRES_VIDES })
const vue = ref<VueIntendance | null>(null)
const chargement = ref(false)
const erreur = ref('')
const tri = ref<{ cle: CleTri; sens: Sens } | null>(null)
const parcoursVus = reactive(new Map<string, string>())
const cohortesVues = reactive(new Map<string, string>())
const selection = ref<string | null>(null)
let declencheur: HTMLElement | null = null
const titreListe = ref<HTMLElement | null>(null)

const lignes = computed(() => {
  const l = vue.value?.lignes ?? []
  return tri.value ? trier(l, tri.value.cle, tri.value.sens) : l
})
const lienExport = computed(() => cas.lienExport.executer(appliques.value))
const optionsParcours = computed(() =>
  [...parcoursVus.entries()]
    .sort((a, b) => a[1].localeCompare(b[1], 'fr'))
    .map(([valeur, titre]) => ({ valeur, titre })),
)
const optionsCohortes = computed(() =>
  [...cohortesVues.entries()]
    .sort((a, b) => a[1].localeCompare(b[1], 'fr'))
    .map(([valeur, titre]) => ({ valeur, titre })),
)
const triMobile = computed({
  get: () => (tri.value ? `${tri.value.cle}:${tri.value.sens}` : ''),
  set: (v: string) => {
    const [cle, sens] = v.split(':') as [CleTri, Sens]
    tri.value = v ? { cle, sens } : null
  },
})

function retenirOptions(l: LigneIntendance[]) {
  for (const x of l) {
    parcoursVus.set(x.parcours, x.titre)
    if (x.cohorte) cohortesVues.set(x.cohorte, x.cohorte_titre || x.cohorte)
  }
}

async function charger() {
  chargement.value = true
  erreur.value = ''
  try {
    vue.value = await cas.consulterIntendance.executer(appliques.value)
    retenirOptions(vue.value.lignes)
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    chargement.value = false
  }
}

function filtrer() {
  appliques.value = { ...filtres }
  return charger()
}

function effacer() {
  Object.assign(filtres, FILTRES_VIDES)
  return filtrer()
}

function trierPar(cle: CleTri) {
  tri.value = tri.value?.cle === cle ? { cle, sens: tri.value.sens === 'asc' ? 'desc' : 'asc' } : { cle, sens: 'asc' }
}

function ariaSort(cle: CleTri) {
  if (tri.value?.cle !== cle) return 'none'
  return tri.value.sens === 'asc' ? 'ascending' : 'descending'
}

function ouvrir(dossier: string, evenement: Event) {
  declencheur = evenement.currentTarget as HTMLElement
  selection.value = dossier
}

async function fermer() {
  selection.value = null
  await nextTick()
  // la ligne a pu quitter la liste (filtre de statut) : le focus revient alors au titre de la liste
  if (declencheur?.isConnected) declencheur.focus()
  else titreListe.value?.focus()
}

function part(l: LigneIntendance) {
  return l.total > 0 ? Math.min(100, Math.round((l.paye * 100) / l.total)) : 100
}

const pluriel = (n: number, mot: string) => `${n} ${mot}${n > 1 ? 's' : ''}`

onMounted(() => {
  if (droits.intendance) void charger()
})
</script>

<template>
  <div class="ecran">
    <EnTete compact>
      <NavAgents :droits="droits" />
    </EnTete>
    <main class="contenu">
      <div class="titre-ligne">
        <div>
          <p class="surtitre">Paiements des parcours</p>
          <h1>Intendance</h1>
        </div>
        <a v-if="droits.intendance" class="bouton export" :href="lienExport" download>
          <svg class="icone" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4v11m0 0-4-4m4 4 4-4M5 19h14" /></svg>
          Exporter en Excel
        </a>
      </div>

      <p v-if="!droits.intendance" class="bandeau bandeau-info reserve">
        Cet écran est réservé à l’intendance et à l’administration.
      </p>

      <template v-else>
        <form class="filtres carte" @submit.prevent="filtrer">
          <div class="champ">
            <label for="f-parcours">Parcours</label>
            <select id="f-parcours" v-model="filtres.parcours" name="parcours">
              <option value="">Tous les parcours</option>
              <option v-for="p in optionsParcours" :key="p.valeur" :value="p.valeur">{{ p.titre }}</option>
            </select>
          </div>
          <div class="champ">
            <label for="f-cohorte">Cohorte</label>
            <select id="f-cohorte" v-model="filtres.cohorte" name="cohorte">
              <option value="">Toutes les cohortes</option>
              <option v-for="c in optionsCohortes" :key="c.valeur" :value="c.valeur">{{ c.titre }}</option>
            </select>
          </div>
          <div class="champ">
            <label for="f-mode">Mode</label>
            <select id="f-mode" v-model="filtres.mode" name="mode">
              <option value="">Tous les modes</option>
              <option v-for="m in MODES" :key="m" :value="m">{{ libelleMode(m) }}</option>
            </select>
          </div>
          <div class="champ">
            <label for="f-statut">Statut</label>
            <select id="f-statut" v-model="filtres.statut" name="statut">
              <option value="">Tous les statuts</option>
              <option v-for="s in STATUTS" :key="s.valeur" :value="s.valeur">{{ s.libelle }}</option>
            </select>
          </div>
          <fieldset class="periode">
            <legend>Inscrits entre</legend>
            <div class="dates">
              <label class="sr-only" for="f-du">Du</label>
              <input id="f-du" v-model="filtres.du" name="du" type="date" />
              <span aria-hidden="true">et</span>
              <label class="sr-only" for="f-au">Au</label>
              <input id="f-au" v-model="filtres.au" name="au" type="date" />
            </div>
          </fieldset>
          <div class="boutons-filtres">
            <button type="submit" class="bouton bouton-sombre" :disabled="chargement">Filtrer</button>
            <button type="button" class="bouton effacer" :disabled="chargement" @click="effacer">Effacer</button>
          </div>
        </form>

        <p v-if="erreur" class="bandeau bandeau-erreur" role="alert">{{ erreur }}</p>

        <template v-if="vue">
          <section class="indicateurs" aria-label="Indicateurs">
            <Indicateur libelle="Encaissé ce mois" :valeur="formaterXof(vue.indicateurs.encaisse_mois)" ton="fort" />
            <Indicateur
              libelle="À échoir sous 30 jours"
              :valeur="formaterXof(vue.indicateurs.encours_30j)"
              detail="Échéances à venir non encore réglées"
            />
            <Indicateur
              libelle="En retard"
              :valeur="formaterXof(vue.indicateurs.en_retard.montant)"
              :detail="pluriel(vue.indicateurs.en_retard.apprenants, 'apprenant')"
              :ton="vue.indicateurs.en_retard.montant > 0 ? 'alerte' : 'neutre'"
            />
            <Indicateur
              libelle="Comptes bloqués"
              :valeur="String(vue.indicateurs.bloques)"
              detail="Apprenants dont un parcours est suspendu"
              :ton="vue.indicateurs.bloques > 0 ? 'alerte' : 'neutre'"
            />
          </section>

          <section class="liste" aria-labelledby="titre-liste">
            <div class="liste-tete">
              <h2 id="titre-liste" ref="titreListe" tabindex="-1">
                Apprenants <span class="compte">({{ vue.lignes.length }})</span>
              </h2>
              <div class="tri-mobile">
                <label for="tri-mobile">Trier par</label>
                <select id="tri-mobile" v-model="triMobile">
                  <option v-for="t in TRIS_MOBILE" :key="t.valeur" :value="t.valeur">{{ t.libelle }}</option>
                </select>
              </div>
            </div>
            <p v-if="vue.tronque" class="bandeau bandeau-alerte tronque">
              Liste limitée aux premiers dossiers. Affinez les filtres pour tout voir (l’export suit la même limite).
            </p>
            <p v-if="!vue.lignes.length" class="carte vide">Aucun dossier ne correspond à ces filtres.</p>
            <table v-else class="tableau">
              <caption class="sr-only">
                Dossiers de paiement, triables par colonne
              </caption>
              <thead>
                <tr>
                  <th v-for="c in COLONNES" :key="c.cle" scope="col" :data-cle="c.cle" :aria-sort="ariaSort(c.cle)">
                    <button type="button" class="tri" @click="trierPar(c.cle)">
                      {{ c.libelle }}
                      <svg class="fleche" viewBox="0 0 24 24" aria-hidden="true">
                        <path v-if="ariaSort(c.cle) === 'descending'" d="m7 10 5 5 5-5" />
                        <path v-else-if="ariaSort(c.cle) === 'ascending'" d="m7 14 5-5 5 5" />
                        <path v-else d="m8 9 4-4 4 4M8 15l4 4 4-4" />
                      </svg>
                    </button>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="l in lignes" :key="l.dossier" :class="{ 'ligne-bloquee': l.bloque }">
                  <td data-label="Apprenant" class="cellule-apprenant">
                    <button type="button" class="ouvrir" @click="ouvrir(l.dossier, $event)">
                      <span class="nom">{{ l.nom }}</span>
                      <span class="sr-only"> : ouvrir la fiche</span>
                    </button>
                    <span class="email">{{ l.email }}</span>
                  </td>
                  <td data-label="Parcours">
                    <span class="titre">{{ l.titre }}</span>
                    <span class="sous"
                      >{{ libelleMode(l.mode)
                      }}<template v-if="l.cohorte_titre"> · {{ l.cohorte_titre }}</template></span
                    >
                  </td>
                  <td data-label="Payé / total">
                    <span class="montants"
                      >{{ formaterXof(l.paye) }} <span class="sous">/ {{ formaterXof(l.total) }}</span></span
                    >
                    <span class="barre" aria-hidden="true"><span :style="{ width: `${part(l)}%` }" /></span>
                  </td>
                  <td data-label="Prochaine échéance">
                    <template v-if="l.prochaine">
                      <span class="titre">{{ formaterXof(l.prochaine.montant) }}</span>
                      <span class="sous">{{
                        l.prochaine.date_limite ? formaterJour(l.prochaine.date_limite) : 'Dès que possible'
                      }}</span>
                    </template>
                    <span v-else class="sous">Aucune</span>
                  </td>
                  <td data-label="Statut"><PuceStatut :etat="etatLigne(l)" /></td>
                </tr>
              </tbody>
            </table>
          </section>
        </template>
        <p v-else-if="chargement" class="discret" role="status">Chargement…</p>
      </template>
    </main>
    <FichePaiement v-if="selection" :dossier="selection" @fermer="fermer" @modifie="charger" />
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
.titre-ligne {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
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
.icone {
  width: 18px;
  height: 18px;
  margin-right: 6px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2.2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.bouton-sombre {
  border: none;
  background: var(--ol-navy);
  color: var(--es-sur-sombre);
}
.bouton-sombre:hover {
  background: var(--ol-night, #00132e);
  color: var(--es-sur-sombre);
}

/* filtres : une colonne sur mobile, grille ensuite */
.filtres {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
  padding: 16px;
  margin: 0;
}
@media (min-width: 600px) {
  .filtres {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (min-width: 1024px) {
  .filtres {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}
.champ,
.periode {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.champ label,
.periode legend {
  font-size: 13px;
  font-weight: 600;
  color: var(--ol-navy);
  padding: 0;
}
.periode {
  border: 0;
  margin: 0;
  padding: 0;
}
@media (min-width: 600px) {
  .periode {
    grid-column: span 2;
  }
}
.dates {
  display: flex;
  align-items: center;
  gap: 8px;
}
.dates input {
  flex: 1;
  min-width: 0;
}
select,
input[type='date'] {
  min-height: 44px;
  width: 100%;
  padding: 6px 10px;
  border: 1px solid var(--es-bord-fort);
  border-radius: 10px;
  background: var(--es-surface);
}
.boutons-filtres {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}
@media (min-width: 600px) {
  .boutons-filtres {
    grid-column: span 2;
    justify-content: flex-end;
  }
}

/* indicateurs : un par ligne sur petit mobile (montants entiers, jamais coupés), deux, puis quatre */
.indicateurs {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}
@media (min-width: 480px) {
  .indicateurs {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (min-width: 900px) {
  .indicateurs {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

.liste-tete {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
.liste h2 {
  margin: 0;
  font-size: 19px;
}
.compte {
  color: var(--es-gris);
  font-weight: 600;
}
.tri-mobile {
  display: flex;
  align-items: center;
  gap: 8px;
}
.tri-mobile label {
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}
.tri-mobile select {
  width: auto;
}
.vide {
  margin: 0;
  padding: 20px;
  text-align: center;
  color: var(--es-gris);
}
.tronque {
  margin-bottom: 8px;
}

/* tableau : cartes sur mobile (chaque cellule nommée), tableau à partir de 768 px */
.tableau {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}
.tableau thead {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  /* en cartes, le tri passe par la liste déroulante : les boutons d'en-tête ne prennent pas le focus */
  visibility: hidden;
}
.tableau tbody {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.tableau tr {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 10px 12px;
  padding: 14px;
  background: var(--es-surface);
  border: 1px solid var(--es-bord);
  border-radius: 14px;
  box-shadow: 0 4px 14px rgba(0, 30, 72, 0.05);
}
.tableau tr.ligne-bloquee {
  border-left: 5px solid var(--ol-navy);
}
.tableau td {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  overflow-wrap: anywhere;
}
.tableau td::before {
  content: attr(data-label);
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--es-gris);
}
.tableau td.cellule-apprenant {
  grid-column: 1 / -1;
}
.tableau td.cellule-apprenant::before {
  content: none;
}
.tableau td:last-child {
  align-items: flex-start;
}
@media (min-width: 768px) {
  .tri-mobile {
    display: none;
  }
  .tableau {
    background: var(--es-surface);
    border: 1px solid var(--es-bord);
    border-radius: 14px;
    box-shadow: 0 4px 14px rgba(0, 30, 72, 0.05);
    overflow: hidden;
  }
  .tableau thead {
    position: static;
    width: auto;
    height: auto;
    overflow: visible;
    clip: auto;
    display: table-header-group;
    visibility: visible;
  }
  .tableau tbody {
    display: table-row-group;
  }
  .tableau tr {
    display: table-row;
    padding: 0;
    border: 0;
    border-radius: 0;
    box-shadow: none;
  }
  .tableau tr.ligne-bloquee {
    border-left: 0;
  }
  .tableau tr.ligne-bloquee td:first-child {
    box-shadow: inset 5px 0 0 var(--ol-navy);
  }
  .tableau th,
  .tableau td {
    display: table-cell;
    padding: 12px 14px;
    text-align: left;
    vertical-align: middle;
    border-bottom: 1px solid var(--es-bord);
  }
  .tableau tbody tr:last-child td {
    border-bottom: 0;
  }
  .tableau tbody tr:hover td {
    background: var(--ol-ivory);
  }
  .tableau td::before,
  .tableau td.cellule-apprenant::before {
    content: none;
  }
  .tableau th {
    background: var(--ol-mist);
    padding: 0;
  }
  .tableau td > span:not(.puce-statut) {
    display: block;
  }
}
.tri {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  width: 100%;
  min-height: 44px;
  padding: 0 14px;
  border: 0;
  background: transparent;
  font-size: 12.5px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--ol-navy);
  text-align: left;
}
.tri:hover {
  background: var(--es-bord-fort);
}
.fleche {
  width: 14px;
  height: 14px;
  flex: none;
  fill: none;
  stroke: currentColor;
  stroke-width: 2.4;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.ouvrir {
  align-self: flex-start;
  padding: 0;
  border: 0;
  background: none;
  font-weight: 600;
  font-size: 16px;
  color: var(--ol-navy-soft);
  text-align: left;
  text-decoration: underline;
  text-decoration-thickness: 1px;
  text-underline-offset: 3px;
}
.ouvrir:hover {
  color: var(--ol-navy);
  text-decoration-thickness: 2px;
}
.email,
.sous {
  font-size: 13px;
  color: var(--es-gris);
}
.titre,
.montants {
  font-weight: 600;
}
.barre {
  display: block;
  height: 6px;
  margin-top: 4px;
  max-width: 160px;
  border-radius: 999px;
  background: var(--ol-mist);
  overflow: hidden;
}
.barre span {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: var(--ol-navy-soft);
}
</style>
