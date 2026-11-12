/* Parcours bloqué, fermé ou caché : une réponse d'API « ParcoursBloque » renvoie vers la page de paiement du
   parcours, « ParcoursFerme » vers sa page /parcours-ferme/, « ParcoursCache » vers le catalogue.
   Le serveur refuse de toute façon ; ce script ne fait que la redirection pendant la navigation dans l'interface. */
(function () {
  'use strict'
  var w = window
  // type d'erreur -> destination admise : un préfixe (nom de parcours à la suite) ou un chemin exact
  var DESTINATIONS = {
    ParcoursBloque: { prefixe: '/espace/paiement/' },
    ParcoursFerme: { prefixe: '/parcours-ferme/' },
    ParcoursCache: { exact: '/lms/courses' },
  }
  if (typeof w.fetch !== 'function' || w.fetch.openlabPaiement) return
  var origine = w.fetch

  // seul un chemin du même site, dans la destination admise pour ce type d'erreur, est suivi (jamais une URL
  // fournie ailleurs)
  function cible(corps) {
    if (!corps || typeof corps.redirection !== 'string') return null
    var dest = Object.prototype.hasOwnProperty.call(DESTINATIONS, corps.exc_type) ? DESTINATIONS[corps.exc_type] : null
    if (!dest) return null
    var url
    try {
      url = new URL(corps.redirection, w.location.origin)
    } catch (e) {
      return null
    }
    if (url.origin !== w.location.origin) return null
    if (dest.exact ? url.pathname !== dest.exact : url.pathname.indexOf(dest.prefixe) !== 0) return null
    return url.pathname
  }

  function enveloppe() {
    return origine.apply(this, arguments).then(function (reponse) {
      var type = (reponse.headers && reponse.headers.get('content-type')) || ''
      if (reponse.ok || type.indexOf('application/json') === -1) return reponse
      // copie lue à part : l'appelant reçoit la réponse intacte
      reponse
        .clone()
        .json()
        .then(function (corps) {
          var chemin = cible(corps)
          if (chemin) w.location.assign(chemin)
        })
        .catch(function () {})
      return reponse
    })
  }
  enveloppe.openlabPaiement = true
  w.fetch = enveloppe
})()
