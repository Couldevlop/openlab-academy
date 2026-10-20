// Dates reçues de Frappe (« 2026-11-03 21:12:00 ») affichées à la française.
const format = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' })

export function formaterDate(valeur) {
  if (!valeur) return ''
  const date = new Date(String(valeur).replace(' ', 'T'))
  return Number.isNaN(date.getTime()) ? '' : format.format(date)
}

/** Lien externe affichable : http(s) seulement (jamais javascript:, data:…). */
export function lienSur(url) {
  return /^https?:\/\//i.test(String(url ?? '')) ? url : ''
}
