import { createRouter, createWebHistory, type RouteRecordRaw, type RouterHistory } from 'vue-router'
import Accueil from './ecrans/Accueil.vue'
import Correcteur from './ecrans/Correcteur.vue'
import Finances from './ecrans/Finances.vue'
import Intendance from './ecrans/Intendance.vue'
import Lots from './ecrans/Lots.vue'
import Paiement from './ecrans/Paiement.vue'
import Relecture from './ecrans/Relecture.vue'
import Retour from './ecrans/Retour.vue'

declare module 'vue-router' {
  interface RouteMeta {
    titre?: string
  }
}

export const routes: RouteRecordRaw[] = [
  { path: '/', name: 'accueil', component: Accueil, meta: { titre: 'Mon espace' } },
  { path: '/relecture/:relecture?', name: 'relecture', component: Relecture, meta: { titre: 'Relecture' } },
  { path: '/correcteur/:copie?', name: 'correcteur', component: Correcteur, meta: { titre: 'Correcteur' } },
  { path: '/lots', name: 'lots', component: Lots, meta: { titre: 'Lots' } },
  { path: '/retour/:copie', name: 'retour', component: Retour, meta: { titre: 'Mon retour' } },
  { path: '/paiement/:cours', name: 'paiement', component: Paiement, meta: { titre: 'Mes paiements' } },
  { path: '/intendance', name: 'intendance', component: Intendance, meta: { titre: 'Intendance' } },
  { path: '/finances', name: 'finances', component: Finances, meta: { titre: 'Finances' } },
  { path: '/:chemin(.*)*', redirect: '/' },
]

export function creerRouteur(historique: RouterHistory = createWebHistory('/espace/')) {
  const routeur = createRouter({ history: historique, routes })
  routeur.afterEach((vers) => {
    document.title = `${vers.meta.titre || 'Mon espace'} · OpenLab Academy`
  })
  return routeur
}

/** Paramètre de route lu comme un texte (le premier d'une liste, vide en son absence). */
export function parametre(valeur: string | null | Array<string | null> | undefined): string {
  return (Array.isArray(valeur) ? valeur[0] : valeur) ?? ''
}
