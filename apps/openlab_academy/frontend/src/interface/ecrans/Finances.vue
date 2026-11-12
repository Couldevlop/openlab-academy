<script setup lang="ts">
// Finances (administration) : vue résumée. Encaissé du mois et son évolution, taux de recouvrement, retards dont
// bloqués ; tableau par parcours ; répartition des modes ; dernières actions de l'équipe ; accès aux prix et à
// l'enregistrement d'un virement (écran Intendance).
import { computed, onMounted, ref } from 'vue'
import { messageErreur } from '../../application/erreurs'
import { formaterHorodatage, isoHorodatage, libelleAction, type ResumeFinances } from '../../domaine/intendance'
import { MODES, formaterXof, libelleMode } from '../../domaine/paiement'
import EnTete from '../composants/EnTete.vue'
import Indicateur from '../composants/Indicateur.vue'
import NavAgents from '../composants/NavAgents.vue'
import { utiliserCasUsages } from '../injection'

const FINE = ' '
const PRIX = '/app/tarif-parcours-openlab'

const cas = utiliserCasUsages()
const droits = cas.consulterDroits.executer()
const resume = ref<ResumeFinances | null>(null)
const chargement = ref(false)
const erreur = ref('')

const nombre = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 1 })
const pourcent = (n: number) => `${nombre.format(n)}${FINE}%`

const evolution = computed(() => {
  const e = resume.value?.evolution_pct
  if (e == null) return 'Pas de comparaison possible avec le mois dernier'
  const signe = e > 0 ? '+' : e < 0 ? '−' : ''
  return `${signe}${pourcent(Math.abs(e))} par rapport au mois dernier à date`
})
const totaux = computed(() =>
  (resume.value?.par_parcours ?? []).reduce(
    (t, p) => ({ inscrits: t.inscrits + p.inscrits, encaisse: t.encaisse + p.encaisse, reste: t.reste + p.reste }),
    { inscrits: 0, encaisse: 0, reste: 0 },
  ),
)
const modes = computed(() => {
  const r = resume.value
  if (!r) return []
  const total = MODES.reduce((s, m) => s + r.modes[m], 0)
  return MODES.map((m) => ({
    mode: m,
    nombre: r.modes[m],
    part: total ? Math.round((r.modes[m] * 100) / total) : 0,
  }))
})

async function charger() {
  chargement.value = true
  erreur.value = ''
  try {
    resume.value = await cas.consulterResume.executer()
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    chargement.value = false
  }
}

onMounted(() => {
  if (droits.finances) void charger()
})
</script>

<template>
  <div class="ecran">
    <EnTete compact>
      <NavAgents :droits="droits" />
    </EnTete>
    <main class="contenu">
      <div>
        <p class="surtitre">Paiements des parcours</p>
        <h1>Finances</h1>
      </div>

      <p v-if="!droits.finances" class="bandeau bandeau-info reserve">Cet écran est réservé à l’administration.</p>
      <p v-if="erreur" class="bandeau bandeau-erreur" role="alert">{{ erreur }}</p>
      <p v-if="chargement && !resume" class="discret" role="status">Chargement…</p>

      <template v-if="resume">
        <section class="indicateurs" aria-label="Indicateurs">
          <Indicateur
            libelle="Encaissé ce mois"
            :valeur="formaterXof(resume.encaisse_mois)"
            :detail="evolution"
            ton="fort"
          />
          <Indicateur
            libelle="Taux de recouvrement"
            :valeur="resume.taux_recouvrement == null ? '—' : pourcent(resume.taux_recouvrement)"
            detail="Part des sommes exigibles déjà réglées"
          />
          <Indicateur
            libelle="Apprenants en retard"
            :valeur="String(resume.retards)"
            :detail="resume.bloques ? `dont ${resume.bloques} ${resume.bloques > 1 ? 'bloqués' : 'bloqué'}` : ''"
            :ton="resume.retards > 0 ? 'alerte' : 'neutre'"
          />
        </section>

        <div class="grille">
          <section class="carte bloc parcours" aria-labelledby="titre-parcours">
            <h2 id="titre-parcours">Par parcours</h2>
            <p v-if="!resume.par_parcours.length" class="discret aucun-parcours">
              Aucun dossier de paiement pour le moment.
            </p>
            <table v-else class="par-parcours">
              <thead>
                <tr>
                  <th scope="col">Parcours</th>
                  <th scope="col" class="nombre">Inscrits</th>
                  <th scope="col" class="nombre">Encaissé</th>
                  <th scope="col" class="nombre">Reste dû</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in resume.par_parcours" :key="p.parcours">
                  <th scope="row" class="nom-parcours">
                    <span>{{ p.titre }}</span>
                  </th>
                  <td class="nombre" data-label="Inscrits">{{ p.inscrits }}</td>
                  <td class="nombre" data-label="Encaissé">{{ formaterXof(p.encaisse) }}</td>
                  <td class="nombre" data-label="Reste dû">{{ formaterXof(p.reste) }}</td>
                </tr>
              </tbody>
              <tfoot>
                <tr>
                  <th scope="row">Total</th>
                  <td class="nombre" data-label="Inscrits">{{ totaux.inscrits }}</td>
                  <td class="nombre" data-label="Encaissé">{{ formaterXof(totaux.encaisse) }}</td>
                  <td class="nombre" data-label="Reste dû">{{ formaterXof(totaux.reste) }}</td>
                </tr>
              </tfoot>
            </table>
          </section>

          <div class="colonne">
            <section class="carte bloc" aria-labelledby="titre-modes">
              <h2 id="titre-modes">Répartition des modes</h2>
              <ul class="modes">
                <li v-for="m in modes" :key="m.mode">
                  <span class="mode-ligne">
                    <span>{{ libelleMode(m.mode) }}<span class="sr-only"> : </span></span>
                    <strong
                      >{{ m.nombre }} <span class="discret">({{ m.part }}{{ FINE }}%)</span></strong
                    >
                  </span>
                  <span class="barre" aria-hidden="true"><span :style="{ width: `${m.part}%` }" /></span>
                </li>
              </ul>
            </section>

            <section class="carte bloc acces" aria-labelledby="titre-acces">
              <h2 id="titre-acces">Accès rapides</h2>
              <a class="bouton prix" :href="PRIX">Prix des parcours</a>
              <RouterLink class="bouton bouton-principal virement" :to="{ name: 'intendance' }">
                Ouvrir l’Intendance
              </RouterLink>
              <p class="discret petit">Le virement s’enregistre depuis la fiche de l’apprenant, dans l’Intendance.</p>
            </section>
          </div>
        </div>

        <section class="carte bloc" aria-labelledby="titre-actions">
          <h2 id="titre-actions">Dernières actions de l’équipe</h2>
          <ol v-if="resume.dernieres_actions.length" class="actions">
            <li v-for="(a, i) in resume.dernieres_actions" :key="i">
              <span class="ligne-un">
                <strong class="action">{{ libelleAction(a.action) }}</strong>
                <time :datetime="isoHorodatage(a.horodatage)">{{ formaterHorodatage(a.horodatage) }}</time>
              </span>
              <span class="concerne">{{ a.nom }} · {{ a.titre }}</span>
              <span class="par"
                >par <span class="acteur">{{ a.acteur }}</span></span
              >
              <p v-if="a.motif" class="motif">{{ a.motif }}</p>
            </li>
          </ol>
          <p v-else class="discret aucune-action">Aucune action pour le moment.</p>
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
  margin: 0 0 12px;
  font-size: 18px;
}
.indicateurs {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}
@media (min-width: 700px) {
  .indicateurs {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
.grille {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
}
@media (min-width: 1000px) {
  .grille {
    grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
    align-items: start;
  }
}
.colonne {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}
.bloc {
  padding: 16px;
  min-width: 0;
}

/* tableau par parcours : cartes sur mobile, tableau à partir de 600 px */
.par-parcours {
  width: 100%;
  border-collapse: collapse;
}
.par-parcours thead {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
}
.par-parcours tr {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 4px 10px;
  padding: 12px 0;
  border-bottom: 1px solid var(--es-bord);
}
.par-parcours tbody th,
.par-parcours tfoot th {
  grid-column: 1 / -1;
  text-align: left;
  font-weight: 600;
  color: var(--ol-navy);
  overflow-wrap: anywhere;
}
.par-parcours td {
  display: flex;
  flex-direction: column;
  min-width: 0;
  font-weight: 600;
}
.par-parcours td::before {
  content: attr(data-label);
  font-size: 11.5px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--es-gris);
}
.par-parcours tfoot tr {
  border-bottom: 0;
  border-top: 2px solid var(--ol-navy);
}
@media (min-width: 600px) {
  .par-parcours thead {
    position: static;
    width: auto;
    height: auto;
    overflow: visible;
    clip: auto;
    display: table-header-group;
  }
  .par-parcours tr {
    display: table-row;
    padding: 0;
  }
  .par-parcours th,
  .par-parcours td {
    display: table-cell;
    padding: 10px 8px;
    text-align: left;
    border-bottom: 1px solid var(--es-bord);
  }
  .par-parcours td::before {
    content: none;
  }
  .par-parcours thead th {
    font-size: 12.5px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--es-gris);
    border-bottom: 2px solid var(--es-bord-fort);
  }
  .par-parcours .nombre {
    text-align: right;
    white-space: nowrap;
  }
  .par-parcours tfoot th,
  .par-parcours tfoot td {
    border-top: 2px solid var(--ol-navy);
    border-bottom: 0;
    font-weight: 700;
    color: var(--ol-navy);
  }
}

.modes {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.mode-ligne {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}
.barre {
  display: block;
  height: 8px;
  margin-top: 4px;
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
.modes li:nth-child(2) .barre span {
  background: var(--ol-sky);
}
.modes li:nth-child(3) .barre span {
  background: var(--ol-orange);
}
.acces {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.acces h2 {
  margin-bottom: 2px;
}
.petit {
  margin: 0;
  font-size: 13px;
}
.actions {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.actions li {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--es-bord);
  border-left: 4px solid var(--ol-navy-soft);
  overflow-wrap: anywhere;
}
.ligne-un {
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}
time,
.par {
  font-size: 13px;
  color: var(--es-gris);
}
.concerne {
  font-weight: 600;
  color: var(--ol-navy);
}
.acteur {
  font-weight: 600;
  color: var(--es-encre);
}
.motif {
  margin: 4px 0 0;
  padding: 6px 10px;
  border-radius: 8px;
  background: var(--ol-ivory);
  white-space: pre-line;
}
</style>
