import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { ErreurDepot } from '../../application/erreurs'
import type { Retour } from '../../domaine/retour'
import { critereRetour, retour } from '../../test/fabriques'
import { fauxPorts } from '../../test/faux-ports'
import { monterEcran } from '../../test/monter'

async function afficher(r: Retour) {
  const ports = fauxPorts()
  ports.retour.monRetour.mockResolvedValue(r)
  return monterEcran('/retour/C1', ports)
}

enableAutoUnmount(afterEach)

describe('Mon retour', () => {
  it('note en attente tant que les relectures ne sont pas faites', async () => {
    const message = 'Votre note sera visible dès que vous aurez terminé vos relectures.'
    const { w, ports } = await afficher(retour({ masquee: true, message }))
    expect(ports.retour.monRetour).toHaveBeenCalledWith('C1')
    expect(w.find('.attente h2').text()).toBe('Note en attente')
    expect(w.find('.attente p').text()).toBe(message)
    expect(w.find('.attente a').attributes('href')).toBe('/relecture')
    expect(w.find('.valeur').exists()).toBe(false)
    expect(w.find('.criteres').exists()).toBe(false)
  })

  it('note publiée, niveaux et commentaires par critère', async () => {
    const { w } = await afficher(
      retour({
        note: 15,
        note_sur: 20,
        reussite: true,
        commentaire_general: 'Très bonne reformulation.',
        criteres: [
          critereRetour('pertinence', 2, { auto_evaluation: 2 }),
          critereRetour('ancrage', 3, { pairs: ['Pense aux sources.'] }),
        ],
      }),
    )
    expect(w.find('.valeur').text()).toBe('15')
    expect(w.find('.reussi').text()).toBe('Validé')
    expect(w.find('.provisoire').exists()).toBe(false)
    const barres = w.findAll('.barre')
    expect(barres[0]!.findAll('span').map((s) => s.classes()[0])).toEqual(['atteint', 'atteint', 'atteint', 'vide'])
    expect(barres[1]!.findAll('span').map((s) => s.classes()[0])).toEqual(['atteint', 'atteint', 'atteint', 'sommet'])
    expect(w.find('.detail').text()).toBe('Votre auto-évaluation : Satisfaisant.')
    expect(w.find('.pairs').text()).toContain('« Pense aux sources. »')
    expect(w.find('.general').text()).toBe('Très bonne reformulation.')
  })

  it('note non validée', async () => {
    const { w } = await afficher(retour({ note: 6, note_sur: 20, reussite: false, criteres: [critereRetour('a', 0)] }))
    expect(w.find('.non-valide').text()).toBe('Non validé')
  })

  it('mention « provisoire » sur une note provisoire', async () => {
    const message = 'Note provisoire, en attente de validation par le formateur.'
    const { w } = await afficher(
      retour({
        statut: 'provisoire',
        provisoire: true,
        note: 10,
        note_sur: 20,
        reussite: true,
        message,
        criteres: [critereRetour('pertinence', 1)],
      }),
    )
    expect(w.find('.provisoire').text()).toBe('provisoire')
    expect(w.find('.mention').text()).toBe(message)
  })

  it('commentaire du formateur (ou justification IA validée) en texte brut', async () => {
    const piege = '<img src=x onerror=alert(1)> **gras**'
    const { w } = await afficher(
      retour({
        note: 12,
        note_sur: 20,
        reussite: true,
        commentaire_general: piege,
        criteres: [critereRetour('pertinence', 1, { commentaire: piege, pairs: [piege] })],
      }),
    )
    // seule image : le logo de l'en-tête
    expect(w.findAll('img').map((i) => i.attributes('src'))).toEqual(['/assets/openlab_academy/images/logo-email.png'])
    expect(w.find('strong').exists()).toBe(false)
    expect(w.find('.general').text()).toBe(piege)
    expect(w.find('.detail').text()).toBe(piege)
  })

  it('copie en cours de correction : message seul', async () => {
    const { w } = await afficher(retour({ statut: 'a_corriger', message: 'Votre copie est en cours de correction.' }))
    expect(w.find('.bandeau-info').text()).toBe('Votre copie est en cours de correction.')
    expect(w.find('.criteres').exists()).toBe(false)
  })

  it('erreur d’accès affichée clairement', async () => {
    const ports = fauxPorts()
    ports.retour.monRetour.mockRejectedValue(new ErreurDepot('acces_refuse'))
    const { w } = await monterEcran('/retour/C9', ports)
    expect(w.find('[role="alert"]').text()).toContain("n'existe pas ou ne vous est pas ouvert")
  })

  it('réponse malformée : message clair, rien d’affiché à moitié', async () => {
    const ports = fauxPorts()
    ports.retour.monRetour.mockRejectedValue(
      new ErreurDepot('reponse_invalide', ['mon_retour.note : attendu un nombre']),
    )
    const { w } = await monterEcran('/retour/C1', ports)
    expect(w.find('[role="alert"]').text()).toContain('Le serveur a répondu de façon inattendue.')
    expect(w.find('h1').exists()).toBe(false)
  })

  it('autre copie dans l’adresse : le retour est rechargé', async () => {
    const { routeur, ports } = await afficher(retour())
    await routeur.push('/retour/C2')
    expect(ports.retour.monRetour).toHaveBeenLastCalledWith('C2')
  })
})
