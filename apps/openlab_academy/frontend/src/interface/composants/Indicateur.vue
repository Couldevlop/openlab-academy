<script setup lang="ts">
// Indicateur en carte : libellé, valeur en grand chiffre, précision facultative. Le ton ne change que le filet de
// gauche et la teinte du chiffre : le sens est toujours porté par le texte.
withDefaults(defineProps<{ libelle: string; valeur: string; detail?: string; ton?: 'neutre' | 'alerte' | 'fort' }>(), {
  detail: '',
  ton: 'neutre',
})
</script>

<template>
  <div class="indicateur" :class="`ton-${ton}`">
    <p class="libelle">{{ libelle }}</p>
    <p class="valeur">{{ valeur }}</p>
    <p v-if="detail" class="detail">{{ detail }}</p>
  </div>
</template>

<style scoped>
.indicateur {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  padding: 14px 16px 14px 20px;
  border-radius: 14px;
  background: var(--es-surface);
  border: 1px solid var(--es-bord);
  box-shadow: 0 4px 14px rgba(0, 30, 72, 0.05);
  overflow: hidden;
}
.indicateur::before {
  content: '';
  position: absolute;
  inset: 0 auto 0 0;
  width: 5px;
  background: var(--ol-navy-soft);
}
.ton-alerte::before {
  background: var(--ol-orange);
}
.ton-fort {
  background: var(--ol-navy);
  border-color: var(--ol-navy);
  color: var(--es-sur-sombre);
}
.ton-fort::before {
  background: var(--ol-filet, var(--ol-orange));
  inset: 0 0 auto 0;
  width: auto;
  height: 4px;
}
p {
  margin: 0;
}
.libelle {
  font-size: 12.5px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--es-gris);
}
.valeur {
  font-family: var(--ol-font-display);
  font-size: 26px;
  font-weight: 700;
  line-height: 1.2;
  color: var(--ol-navy);
  overflow-wrap: break-word;
}
.ton-alerte .valeur {
  color: #8a3300;
}
.detail {
  font-size: 13.5px;
  color: var(--es-gris);
}
.ton-fort .libelle,
.ton-fort .detail,
.ton-fort .valeur {
  color: var(--es-sur-sombre);
}
</style>
