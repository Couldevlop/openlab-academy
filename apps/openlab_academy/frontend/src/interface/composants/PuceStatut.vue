<script setup lang="ts">
// Pastille d'état d'un dossier de paiement : une icône et le libellé écrit, jamais la couleur seule (contraste AA).
import { computed } from 'vue'
import { libelleEtat, type EtatLigne } from '../../domaine/intendance'

const props = defineProps<{ etat: EtatLigne }>()
const libelle = computed(() => libelleEtat(props.etat))
</script>

<template>
  <span class="puce-statut" :class="`etat-${etat}`">
    <svg class="icone" viewBox="0 0 24 24" aria-hidden="true">
      <template v-if="etat === 'bloque'">
        <rect x="5" y="11" width="14" height="9" rx="2" />
        <path d="M8 11V8a4 4 0 0 1 8 0v3" />
      </template>
      <template v-else-if="etat === 'en_retard'">
        <circle cx="12" cy="12" r="8" />
        <path d="M12 8v4l3 2" />
      </template>
      <template v-else-if="etat === 'rappel_envoye'">
        <path d="M4 6h16v12H4z" />
        <path d="m4 7 8 6 8-6" />
      </template>
      <template v-else-if="etat === 'dispense'">
        <path d="M6 12h12" />
      </template>
      <path v-else d="m5 12.5 4.5 4.5L19 7.5" />
    </svg>
    {{ libelle }}
  </span>
</template>

<style scoped>
.puce-statut {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 11px 3px 8px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  line-height: 1.4;
  white-space: nowrap;
}
.icone {
  width: 15px;
  height: 15px;
  flex: none;
  fill: none;
  stroke: currentColor;
  stroke-width: 2.4;
  stroke-linecap: round;
  stroke-linejoin: round;
}
/* contrastes du texte sur son fond, tous ≥ 4,5:1 */
.etat-a_jour {
  background: #dcf2e3;
  color: #14532d;
}
.etat-rappel_envoye {
  background: #e4ebf8;
  color: var(--ol-navy-soft, #244498);
}
.etat-en_retard {
  background: #ffe6d4;
  color: #8a3300;
}
.etat-bloque {
  background: var(--ol-navy, #001e48);
  color: var(--es-sur-sombre, #fff);
}
.etat-solde {
  background: var(--ol-sun, #fcd80f);
  color: var(--ol-navy, #001e48);
}
.etat-dispense {
  background: var(--ol-mist, #eef1f6);
  color: #4a5164;
}
</style>
