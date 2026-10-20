<script setup>
// Grille du correcteur : par critère, les niveaux avec leurs sources (A, IA, P, J), le choix du formateur,
// l'écart IA / pairs, la justification de l'IA et un commentaire facultatif. Tout texte est interpolé (échappé).
import { computed } from 'vue'
import { ecart, formaterNombre } from '../lib/grille'
import Puce from './Puce.vue'

const props = defineProps({
  grille: { type: Object, required: true },
  niveaux: { type: Object, required: true },
  commentaires: { type: Object, required: true },
  actif: { type: String, default: '' },
  auto: { type: Object, default: null },
  ia: { type: Object, default: null },
  pairs: { type: Object, default: () => ({ mediane: {}, nombre: 0, commentaires: [] }) },
  jury: { type: Object, default: () => ({ mediane: {}, nombre: 0 }) },
})
const emit = defineEmits(['update:niveaux', 'update:commentaires', 'update:actif'])

const avecPairs = computed(() => props.pairs?.nombre > 0)
const avecJury = computed(() => props.jury?.nombre > 0)

function sources(code, i) {
  return {
    auto: props.auto?.[code] === i,
    ia: props.ia?.niveaux?.[code] === i,
    pairs: avecPairs.value && props.pairs.mediane?.[code] === i,
    jury: avecJury.value && props.jury.mediane?.[code] === i,
  }
}

function lecture(s) {
  return [s.auto && 'auto-évaluation', s.ia && 'IA', s.pairs && 'médiane des pairs', s.jury && 'médiane du jury']
    .filter(Boolean)
    .join(', ')
}

const criteres = computed(() =>
  props.grille.criteres.map((c) => ({
    ...c,
    ecart: avecPairs.value && ecart(props.ia?.niveaux?.[c.code], props.pairs.mediane?.[c.code]),
    justification: props.ia?.justifications?.[c.code] || '',
    remarquesPairs: (props.pairs?.commentaires || []).map((p) => p?.[c.code]).filter(Boolean),
    niveaux: c.niveaux.map((n, i) => ({ ...n, i, s: sources(c.code, i) })),
  })),
)

const confiance = computed(() => (props.ia?.confiance == null ? '' : formaterNombre(props.ia.confiance)))

function choisir(code, i) {
  emit('update:actif', code)
  emit('update:niveaux', { ...props.niveaux, [code]: i })
}

function commenter(code, texte) {
  emit('update:commentaires', { ...props.commentaires, [code]: texte })
}
</script>

<template>
  <div class="grille">
    <div class="legende">
      <span v-if="auto"><Puce sorte="A" />auto-évaluation</span>
      <span v-if="ia"><Puce sorte="IA" />pré-correction</span>
      <span v-if="avecPairs"><Puce sorte="P" />médiane des pairs ({{ pairs.nombre }})</span>
      <span v-if="avecJury"><Puce sorte="J" />médiane du jury</span>
    </div>

    <section
      v-for="c in criteres"
      :key="c.code"
      class="critere"
      :class="{ actif: c.code === actif }"
      :data-critere="c.code"
      @focusin="emit('update:actif', c.code)"
    >
      <div class="critere-tete">
        <h3 :id="`critere-${c.code}`">{{ c.libelle }}</h3>
        <span class="discret">{{ c.poids }} %</span>
      </div>
      <div
        class="niveaux"
        role="group"
        :aria-labelledby="`critere-${c.code}`"
        :style="{ '--n': c.niveaux.length }"
      >
        <button
          v-for="n in c.niveaux"
          :key="n.i"
          type="button"
          class="niveau"
          :aria-pressed="niveaux[c.code] === n.i ? 'true' : 'false'"
          :title="n.descripteur"
          @click="choisir(c.code, n.i)"
        >
          <span>{{ n.libelle }}</span>
          <span class="puces">
            <Puce v-if="n.s.auto" sorte="A" :inverse="niveaux[c.code] === n.i" />
            <Puce v-if="n.s.ia" sorte="IA" :inverse="niveaux[c.code] === n.i" />
            <Puce v-if="n.s.pairs" sorte="P" :inverse="niveaux[c.code] === n.i" />
            <Puce v-if="n.s.jury" sorte="J" :inverse="niveaux[c.code] === n.i" />
            <span v-if="lecture(n.s)" class="sr-only">({{ lecture(n.s) }})</span>
          </span>
        </button>
      </div>
      <p v-if="c.ecart" class="ecart">L'IA et les pairs divergent de plus d'un niveau : à trancher.</p>
      <p v-if="c.justification" class="ia-ligne discret">
        IA<template v-if="confiance">, confiance {{ confiance }}</template> : « {{ c.justification }} »
      </p>
      <details v-if="c.remarquesPairs.length" class="pairs">
        <summary>Commentaires des pairs ({{ c.remarquesPairs.length }})</summary>
        <ul>
          <li v-for="(r, k) in c.remarquesPairs" :key="k">« {{ r }} »</li>
        </ul>
      </details>
      <details class="commentaire" :open="!!commentaires[c.code]">
        <summary>Commentaire sur ce critère</summary>
        <label class="sr-only" :for="`commentaire-${c.code}`">Commentaire sur « {{ c.libelle }} »</label>
        <textarea
          :id="`commentaire-${c.code}`"
          rows="2"
          maxlength="5000"
          :value="commentaires[c.code] || ''"
          @input="commenter(c.code, $event.target.value)"
        />
      </details>
    </section>
  </div>
</template>

<style scoped>
.legende { display: flex; flex-wrap: wrap; gap: 8px 14px; margin: 0 0 22px; font-size: 13px; color: var(--es-gris); }
.legende > span { display: inline-flex; align-items: center; gap: 6px; }
.critere { padding: 18px 0; border-top: 1px solid var(--es-bord); position: relative; }
.critere.actif::before {
  content: ''; position: absolute; left: -16px; top: 18px; bottom: 18px; width: 3px; border-radius: 2px;
  background: var(--ol-orange);
}
.critere-tete { display: flex; justify-content: space-between; gap: 12px; margin-bottom: 10px; }
.critere-tete h3 { margin: 0; font-size: 16px; font-weight: 600; }
.critere-tete span { font-size: 14px; white-space: nowrap; }
.niveaux { display: grid; gap: 6px; grid-template-columns: repeat(2, minmax(0, 1fr)); }
.niveau {
  min-height: 64px; padding: 8px 6px; font-size: 12.5px; line-height: 1.25;
  display: flex; flex-direction: column; justify-content: space-between; gap: 6px; overflow-wrap: break-word;
}
.puces { display: flex; flex-wrap: wrap; gap: 3px; min-height: 18px; }
.ecart {
  margin: 10px 0 0; padding: 8px 12px; border-radius: 8px; background: var(--es-alerte-fond);
  color: var(--es-alerte-texte); font-size: 13.5px;
}
.ia-ligne { margin: 10px 0 0; font-size: 13.5px; overflow-wrap: anywhere; white-space: pre-line; }
.pairs, .commentaire { margin-top: 10px; font-size: 13.5px; }
.pairs summary, .commentaire summary { font-weight: 500; color: var(--es-gris); }
.pairs ul { margin: 6px 0 0; padding-left: 18px; white-space: pre-line; overflow-wrap: anywhere; }
.commentaire textarea { margin-top: 6px; font-size: 14px; }
@media (min-width: 480px) {
  .niveaux { grid-template-columns: repeat(var(--n), minmax(0, 1fr)); }
}
@media (max-width: 420px) {
  .critere.actif::before { left: -10px; }
}
</style>
