// Requête Frappe de frappe-ui, prise à sa source par l'alias de vite.config.ts (seule cette fonction est embarquée).
declare module 'frappe-ui-requete' {
  import type { RequeteFrappe } from './infrastructure/frappe/client'

  export const frappeRequest: RequeteFrappe
}

// jeton CSRF de la session, posé par www/espace.html
interface Window {
  csrf_token?: string
}
