/**
 * Le filtre par famille du catalogue.
 *
 * Il ne demande rien au serveur : les cartes sont déjà toutes là, rendues par lui. Filtrer par un appel
 * d'API ferait attendre le visiteur pour masquer des éléments qu'il a sous les yeux, et rendrait la page
 * inutilisable sans JavaScript — or c'est la page que l'on cherche.
 */
(function () {
  'use strict'

  const filtres = document.querySelector('[data-role="filtres"]')
  const cartes = document.querySelector('[data-role="cartes"]')
  if (!filtres || !cartes) return

  const boutons = Array.from(filtres.querySelectorAll('.ol-filtre'))

  function appliquer(categorie) {
    boutons.forEach((b) => {
      const actif = b.dataset.categorie === categorie
      b.classList.toggle('ol-filtre--actif', actif)
      b.setAttribute('aria-pressed', String(actif))
    })
    Array.from(cartes.children).forEach((carte) => {
      carte.hidden = Boolean(categorie) && carte.dataset.domaine !== categorie
    })
  }

  filtres.addEventListener('click', (evenement) => {
    const bouton = evenement.target.closest('.ol-filtre')
    if (bouton) appliquer(bouton.dataset.categorie)
  })

  appliquer('')
})()
