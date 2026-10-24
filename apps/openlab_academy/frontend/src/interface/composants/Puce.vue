<script setup lang="ts">
// Pastille de source d'un niveau : A (auto-évaluation), IA (pré-correction), P (médiane des pairs), J (jury).
withDefaults(defineProps<{ sorte: 'A' | 'IA' | 'P' | 'J'; inverse?: boolean }>(), { inverse: false })
</script>

<template>
  <span class="puce" :class="[`puce-${sorte.toLowerCase()}`, { inverse }]" aria-hidden="true">{{ sorte }}</span>
</template>

<style scoped>
.puce {
  display: inline-block;
  min-width: 22px;
  height: 18px;
  padding: 0 3px;
  border-radius: 9px;
  font-size: 10px;
  line-height: 18px;
  text-align: center;
  font-weight: 600;
  font-family: var(--ol-font-body);
}
.puce-a {
  border: 1.5px solid var(--es-gris);
  line-height: 15px;
  color: var(--es-encre);
}
.puce-ia {
  background: var(--ol-navy-soft);
  color: var(--es-sur-sombre);
}
.puce-p,
.puce-j {
  background: var(--es-bord);
  color: var(--es-encre);
}
.puce-j {
  border: 1.5px dashed var(--es-gris);
  line-height: 15px;
}
.inverse.puce-a {
  border-color: var(--es-sur-sombre);
  color: var(--es-sur-sombre);
}
.inverse.puce-ia {
  background: var(--es-surface);
  color: var(--ol-navy);
}
</style>
