<script setup>
defineProps({ compact: { type: Boolean, default: false } })
</script>

<template>
  <header class="entete" :class="{ compact }">
    <a class="marque" href="/lms">OpenLab Academy</a>
    <slot />
  </header>
</template>

<style scoped>
.entete {
  display: flex; flex-wrap: wrap; align-items: center; gap: 8px 16px;
  padding: 14px 16px; background: var(--ol-navy); color: #fff;
}
.marque { color: #fff; text-decoration: none; font-family: var(--ol-font-display); font-weight: 700; font-size: 17px; }
.marque:hover { color: #fff; text-decoration: underline; }
@media (min-width: 768px) {
  .entete:not(.compact) { padding: 14px 32px; }
  .entete:not(.compact) .marque { font-size: 18px; }
}
</style>
