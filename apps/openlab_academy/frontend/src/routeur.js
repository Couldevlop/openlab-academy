import { createRouter, createWebHistory } from 'vue-router'
import Accueil from './ecrans/Accueil.vue'
import Correcteur from './ecrans/Correcteur.vue'
import Lots from './ecrans/Lots.vue'
import Relecture from './ecrans/Relecture.vue'
import Retour from './ecrans/Retour.vue'

export const routes = [
  { path: '/', name: 'accueil', component: Accueil, meta: { titre: 'Mon espace' } },
  { path: '/relecture/:relecture?', name: 'relecture', component: Relecture, meta: { titre: 'Relecture' } },
  { path: '/correcteur/:copie?', name: 'correcteur', component: Correcteur, meta: { titre: 'Correcteur' } },
  { path: '/lots', name: 'lots', component: Lots, meta: { titre: 'Lots' } },
  { path: '/retour/:copie', name: 'retour', component: Retour, meta: { titre: 'Mon retour' } },
  { path: '/:chemin(.*)*', redirect: { name: 'accueil' } },
]

export function creerRouteur(historique = createWebHistory('/espace/')) {
  const routeur = createRouter({ history: historique, routes })
  routeur.afterEach((vers) => {
    document.title = `${vers.meta.titre || 'Mon espace'} · OpenLab Academy`
  })
  return routeur
}
