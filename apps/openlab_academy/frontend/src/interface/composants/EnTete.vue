<script setup lang="ts">
// En-tête des écrans : logo OpenLab Academy sur blanc et actions de l'écran (contenu glissé), souligné du filet aux
// quatre couleurs du logo, comme l'e-mail de rappel.
withDefaults(defineProps<{ compact?: boolean }>(), { compact: false })

const LOGO = '/assets/openlab_academy/images/logo-horizontal.svg'
</script>

<template>
  <header class="entete" :class="{ compact }">
    <div class="ligne-marque">
      <a class="marque" href="/lms"><img :src="LOGO" alt="OpenLab Academy" width="440" height="100" /></a>
      <slot />
    </div>
    <div class="filet" aria-hidden="true" />
  </header>
</template>

<style scoped>
.ligne-marque {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 16px;
  padding: 10px 16px;
  background: var(--es-surface);
  color: var(--es-entete-texte);
}
.marque {
  display: inline-flex;
  margin-right: 8px;
  border-radius: 6px;
}
.marque img {
  display: block;
  width: auto;
  height: 40px;
}
.filet {
  height: 4px;
  background: var(--ol-filet, var(--ol-orange));
  box-shadow: 0 2px 8px rgba(0, 30, 72, 0.08);
}
@media (min-width: 768px) {
  .entete:not(.compact) .ligne-marque {
    padding: 12px 32px;
  }
  .entete:not(.compact) .marque img {
    height: 46px;
  }
}
</style>
