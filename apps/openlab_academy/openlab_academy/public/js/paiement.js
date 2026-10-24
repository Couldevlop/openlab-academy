/* Parcours bloqué : une réponse d'API « ParcoursBloque » renvoie vers la page de paiement du parcours.
   Le serveur refuse de toute façon ; ce script ne fait que la redirection pendant la navigation dans l'interface. */
(function () {
  'use strict'
  var w = window
  var PREFIXE = '/espace/paiement/'
  if (typeof w.fetch !== 'function' || w.fetch.openlabPaiement) return
  var origine = w.fetch

  // seul un chemin du même site sous /espace/paiement/ est suivi (jamais une URL fournie ailleurs)
  function cible(corps) {
    if (!corps || corps.exc_type !== 'ParcoursBloque' || typeof corps.redirection !== 'string') return null
    var url
    try {
      url = new URL(corps.redirection, w.location.origin)
    } catch (e) {
      return null
    }
    if (url.origin !== w.location.origin || url.pathname.indexOf(PREFIXE) !== 0) return null
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
