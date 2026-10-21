<script setup lang="ts">
// Copie de l'apprenant ou consigne : Markdown assaini, citation de l'IA surlignée. Seul le HTML assaini est inséré,
// et ce composant est le seul de l'espace à insérer du HTML.
import { computed, nextTick, ref, watch } from 'vue'
import { rendreMarkdown, surligner } from '../rendu/markdown'

const props = withDefaults(defineProps<{ texte?: string; citation?: string }>(), { texte: '', citation: '' })

const zone = ref<HTMLElement | null>(null)
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
  <!-- eslint-disable-next-line vue/no-v-html -- seul HTML inséré : Markdown sans HTML brut, assaini par DOMPurify -->
  <div ref="zone" class="copie" v-html="rendu.html" />
</template>
