<script setup>
// Copie de l'apprenant : Markdown assaini, citation de l'IA surlignée. Seul le HTML assaini est inséré.
import { computed, nextTick, ref, watch } from 'vue'
import { rendreMarkdown, surligner } from '../lib/markdown'

const props = defineProps({
  texte: { type: String, default: '' },
  citation: { type: String, default: '' },
})

const zone = ref(null)
const assaini = computed(() => rendreMarkdown(props.texte))
const rendu = computed(() => surligner(assaini.value, props.citation))

const sansAnimation = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? true

watch(
  () => [props.citation, rendu.value.html],
  async () => {
    await nextTick()
    const marque = zone.value?.querySelector('mark.citation')
    marque?.scrollIntoView?.({ block: 'nearest', behavior: sansAnimation() ? 'auto' : 'smooth' })
  },
)

defineExpose({ trouvee: computed(() => rendu.value.trouvee) })
</script>

<template>
  <!-- HTML issu de rendreMarkdown (html:false + DOMPurify) puis de surligner (nœuds texte seulement) -->
  <div ref="zone" class="copie" v-html="rendu.html" />
</template>
