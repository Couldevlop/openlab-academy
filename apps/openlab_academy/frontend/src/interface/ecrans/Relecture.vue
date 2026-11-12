<script setup lang="ts">
// Relecture par un pair (apprenant, mobile d'abord) : copie anonyme, un niveau et un conseil bienveillant par
// critère, progression « relecture 2 sur 3 ». Le brouillon reste sur l'appareil en cas de coupure réseau.
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { messageErreur } from '../../application/erreurs'
import { formaterDate } from '../../domaine/dates'
import { descripteurChoisi, descripteurUtile, type Niveaux } from '../../domaine/grille'
import {
  aFaire,
  critereIncomplet,
  prochaineAFaire,
  progression,
  type ResumeRelecture,
  type VueRelecture,
} from '../../domaine/relecture'
import CopieRendue from '../composants/CopieRendue.vue'
import EnTete from '../composants/EnTete.vue'
import { utiliserCasUsages } from '../injection'
import { parametre } from '../routeur'

const cas = utiliserCasUsages()
const route = useRoute()
const router = useRouter()

const liste = ref<ResumeRelecture[]>([])
const vue = ref<VueRelecture | null>(null)
const niveaux = ref<Niveaux>({})
const conseils = ref<Record<string, string>>({})
const tente = ref(false)
const occupe = ref(false)
const erreur = ref('')
const chargement = ref(true)
const terminee = ref(false)

const id = computed(() => parametre(route.params.relecture))
const criteres = computed(() => vue.value?.grille.criteres ?? [])
const ouverte = computed(() => !!vue.value && aFaire(vue.value.statut) && !terminee.value)
const avancement = computed(() =>
  vue.value ? progression(liste.value, vue.value.exercice, vue.value.total) : { faites: 0, sur: 1 },
)
const saisie = () => ({ niveaux: niveaux.value, conseils: conseils.value })
const manque = (code: string) => tente.value && critereIncomplet(saisie(), code)

async function charger() {
  chargement.value = true
  erreur.value = ''
  vue.value = null
  terminee.value = tente.value = false
  try {
    liste.value = await cas.consulterRelectures.executer()
    if (!id.value) {
      const suivante = prochaineAFaire(liste.value)
      if (suivante) await router.replace({ name: 'relecture', params: { relecture: suivante.relecture } })
      return
    }
    const ouverture = await cas.ouvrirRelecture.executer(id.value)
    vue.value = ouverture.vue
    niveaux.value = ouverture.saisie.niveaux
    conseils.value = ouverture.saisie.conseils
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    chargement.value = false
  }
}

onMounted(charger)
watch(id, charger)

function choisir(code: string, i: number) {
  niveaux.value = { ...niveaux.value, [code]: i }
  cas.garderBrouillon.executer(id.value, saisie())
}

function conseiller(code: string, evenement: Event) {
  conseils.value = { ...conseils.value, [code]: (evenement.target as HTMLTextAreaElement).value }
  cas.garderBrouillon.executer(id.value, saisie())
}

async function envoyer() {
  const grille = vue.value?.grille
  if (!grille) return
  tente.value = true
  erreur.value = ''
  occupe.value = true
  try {
    const resultat = await cas.envoyerRelecture.executer(id.value, grille, saisie())
    if (!resultat.envoyee) {
      await nextTick()
      document.getElementById(`critere-${resultat.incomplets[0]}`)?.focus()
      return
    }
    liste.value = resultat.liste
    if (resultat.suivante) await router.push({ name: 'relecture', params: { relecture: resultat.suivante } })
    else terminee.value = true
  } catch (e) {
    erreur.value = messageErreur(e)
  } finally {
    occupe.value = false
  }
}
</script>

<template>
  <div class="ecran">
    <EnTete compact>
      <RouterLink class="lien-espace" :to="{ name: 'accueil' }">Mon espace</RouterLink>
      <span class="espace" />
      <span v-if="vue" class="position">Relecture {{ vue.rang }} sur {{ vue.total }}</span>
    </EnTete>
    <div
      v-if="vue"
      class="progression"
      role="progressbar"
      aria-label="Relectures faites"
      aria-valuemin="0"
      :aria-valuemax="avancement.sur"
      :aria-valuenow="avancement.faites"
    >
      <div :style="{ width: `${(100 * avancement.faites) / avancement.sur}%` }" />
    </div>

    <main class="contenu">
      <p v-if="chargement" class="discret" role="status">Chargement…</p>
      <p v-else-if="erreur && !vue" class="bandeau bandeau-erreur" role="alert">{{ erreur }}</p>

      <section v-else-if="!vue" class="carte fin">
        <h1>Aucune relecture à faire</h1>
        <p>Vos relectures sont à jour. Merci pour vos conseils : ils aident vos pairs à progresser.</p>
      </section>

      <section v-else-if="terminee" class="carte fin" role="status">
        <h1>Relectures terminées</h1>
        <p>Merci ! Votre note, si elle est publiée, vous est désormais visible.</p>
      </section>

      <template v-else>
        <div>
          <p class="surtitre discret">
            <template v-if="vue.anonymat_garanti">Copie anonyme</template>
            <template v-else>Copie rendue par lien</template>
            <template v-if="vue.echeance"> · à relire avant le {{ formaterDate(vue.echeance) }}</template>
          </p>
          <h1>{{ vue.titre }}</h1>
        </div>

        <p v-if="!vue.anonymat_garanti" class="bandeau bandeau-alerte">
          Le dépôt lié peut révéler son auteur : jugez le travail, pas la personne.
        </p>

        <details v-if="vue.consigne" class="carte consigne">
          <summary>Consigne</summary>
          <CopieRendue :texte="vue.consigne" />
        </details>

        <article class="carte texte" aria-label="Copie à relire">
          <CopieRendue :texte="vue.contenu" />
        </article>

        <p v-if="!ouverte" class="bandeau bandeau-info" role="status">Cette relecture est déjà envoyée. Merci !</p>

        <form v-else class="formulaire" novalidate @submit.prevent="envoyer">
          <fieldset
            v-for="c in criteres"
            :id="`critere-${c.code}`"
            :key="c.code"
            class="carte critere"
            tabindex="-1"
            :aria-describedby="manque(c.code) ? `erreur-${c.code}` : undefined"
          >
            <legend class="sr-only">{{ c.libelle }}</legend>
            <h2 aria-hidden="true">{{ c.libelle }}</h2>
            <p v-if="c.description && c.description !== c.libelle" class="discret description">{{ c.description }}</p>
            <div class="niveaux" :style="{ '--n': c.niveaux.length }">
              <button
                v-for="(n, i) in c.niveaux"
                :key="i"
                type="button"
                class="niveau"
                :aria-pressed="niveaux[c.code] === i ? 'true' : 'false'"
                :aria-describedby="descripteurUtile(n) ? `descripteur-${c.code}-${i}` : undefined"
                :title="n.descripteur"
                @click="choisir(c.code, i)"
              >
                {{ n.libelle }}
              </button>
            </div>
            <template v-for="(n, i) in c.niveaux" :key="i">
              <span v-if="descripteurUtile(n)" :id="`descripteur-${c.code}-${i}`" hidden>{{
                descripteurUtile(n)
              }}</span>
            </template>
            <p v-if="descripteurChoisi(c, niveaux)" class="discret descripteur">{{ descripteurChoisi(c, niveaux) }}</p>
            <label :for="`conseil-${c.code}`">Votre conseil</label>
            <textarea
              :id="`conseil-${c.code}`"
              rows="3"
              maxlength="5000"
              required
              placeholder="Un conseil précis et bienveillant, obligatoire"
              :aria-invalid="manque(c.code) && !conseils[c.code]?.trim() ? 'true' : 'false'"
              :value="conseils[c.code] || ''"
              @input="conseiller(c.code, $event)"
            />
            <p v-if="manque(c.code)" :id="`erreur-${c.code}`" class="manque">
              {{
                Number.isInteger(niveaux[c.code])
                  ? 'Ajoutez un conseil.'
                  : 'Choisissez un niveau et ajoutez un conseil.'
              }}
            </p>
          </fieldset>

          <p class="discret">Votre note sera visible une fois vos {{ vue.total }} relectures faites.</p>
          <p v-if="erreur" class="bandeau bandeau-erreur" role="alert">{{ erreur }}</p>
          <button type="submit" class="bouton bouton-principal envoyer" :disabled="occupe">Envoyer ma relecture</button>
        </form>
      </template>
    </main>
  </div>
</template>

<style scoped>
.espace {
  flex-grow: 1;
}
.position {
  color: var(--es-entete-clair);
  font-size: 14px;
}
.progression {
  height: 4px;
  background: var(--es-bord);
}
.progression > div {
  height: 4px;
  background: var(--ol-orange);
}
.contenu {
  max-width: 720px;
  margin: 0 auto;
  padding: 20px 16px 28px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.surtitre {
  margin: 0 0 2px;
  font-size: 13.5px;
}
h1 {
  margin: 0;
  font-size: 23px;
  line-height: 1.2;
  font-weight: 600;
}
.consigne {
  padding: 12px 16px;
}
.consigne :deep(.copie) {
  margin-top: 8px;
  font-size: 15px;
}
.texte {
  padding: 16px;
}
.texte :deep(.copie) {
  font-size: 15px;
  line-height: 1.65;
}
.formulaire {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.critere {
  padding: 16px;
  margin: 0;
  min-width: 0;
}
.critere:focus {
  outline: none;
}
.critere:focus-visible {
  outline: 2px solid var(--ol-orange);
}
.critere h2 {
  margin: 0 0 4px;
  font-family: var(--ol-font-body);
  font-size: 16px;
  font-weight: 600;
}
.description {
  margin: 0 0 12px;
  font-size: 13.5px;
}
.niveaux {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 8px;
}
.niveau {
  min-height: 48px;
  padding: 6px 10px;
  font-size: 14px;
  text-align: center;
}
.descripteur {
  margin: 8px 0 0;
  font-size: 13.5px;
  overflow-wrap: anywhere;
}
label {
  display: block;
  margin: 14px 0 6px;
  font-weight: 600;
  font-size: 14px;
}
textarea {
  font-size: 14px;
}
.manque {
  margin: 6px 0 0;
  color: var(--es-erreur);
  font-size: 13.5px;
}
.envoyer {
  min-height: 50px;
}
.fin {
  padding: 20px 16px;
}
.fin h1 {
  margin-bottom: 8px;
}
.fin p {
  margin: 0;
}
@media (min-width: 768px) {
  .niveaux {
    grid-template-columns: repeat(var(--n), minmax(0, 1fr));
  }
}
</style>
