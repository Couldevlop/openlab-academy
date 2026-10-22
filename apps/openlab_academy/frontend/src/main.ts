// Point d'entrée : branche les cas d'usage sur leurs adaptateurs (Frappe, navigateur) et les fournit aux écrans.
import { frappeRequest } from 'frappe-ui-requete'
import { createApp } from 'vue'
import { creerCasUsages } from './application/cas-usages'
import { creerPorts } from './infrastructure/ports'
import App from './interface/App.vue'
import { CLE_CAS_USAGES } from './interface/injection'
import { creerRouteur } from './interface/routeur'
import './interface/style.css'

const cas = creerCasUsages(
  creerPorts(
    frappeRequest,
    () => window.localStorage,
    () => window.location,
  ),
)

createApp(App).provide(CLE_CAS_USAGES, cas).use(creerRouteur()).mount('#espace')
