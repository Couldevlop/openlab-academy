/**
 * L'inscription depuis la fiche d'un parcours.
 *
 * La page porte déjà son offre, rendue par le serveur : ce script ne fait que l'actualiser et poster
 * l'inscription. Sans lui, la fiche reste juste et le bouton « Me connecter » fonctionne — c'est voulu,
 * une façade doit se lire sans JavaScript.
 *
 * Il n'envoie qu'un nom de parcours. Ni la cohorte, ni le prix, ni l'identité : le serveur les décide, et
 * l'API refuserait de toute façon ce qu'il n'a pas choisi lui-même.
 */
(function () {
  'use strict'

  const offre = document.getElementById('ol-offre')
  if (!offre) return

  const parcours = offre.dataset.parcours
  const bouton = offre.querySelector('[data-role="inscrire"]')
  const refus = offre.querySelector('[data-role="refus"]')

  /** Le jeton CSRF de la session, posé par Frappe. Toute écriture le porte. */
  const jeton = () => (window.frappe && window.frappe.csrf_token) || ''

  function dire(message) {
    if (!refus) return
    refus.textContent = message
    refus.hidden = !message
  }

  /** Le message d'erreur de Frappe, sans la trace : le visiteur n'a pas à lire une pile d'appels. */
  async function messageDe(reponse) {
    try {
      const corps = await reponse.json()
      const messages = JSON.parse(corps._server_messages || '[]')
      if (messages.length) return JSON.parse(messages[0]).message
      if (corps.exc_type === 'ValidationError' && corps.exception) {
        return String(corps.exception).split(': ').slice(1).join(': ')
      }
    } catch (_) { /* une réponse illisible ne doit pas masquer l'échec lui-même */ }
    return "L’inscription n’a pas abouti. Réessayez dans un instant."
  }

  async function inscrire() {
    bouton.disabled = true
    dire('')
    try {
      const reponse = await fetch('/api/method/openlab_academy.entrypoints.site_api.inscrire', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Frappe-CSRF-Token': jeton(),
        },
        body: JSON.stringify({ parcours }),
      })
      if (!reponse.ok) {
        dire(await messageDe(reponse))
        bouton.disabled = false
        return
      }
      const { message } = await reponse.json()
      // La destination vient du serveur et n'est jamais une adresse complète : elle ne peut pas
      // emmener le visiteur hors du site.
      window.location.assign(message && message.destination ? message.destination : '/parcours')
    } catch (_) {
      dire("Connexion interrompue. Vérifiez votre réseau, puis réessayez.")
      bouton.disabled = false
    }
  }

  if (bouton) bouton.addEventListener('click', inscrire)
})()
