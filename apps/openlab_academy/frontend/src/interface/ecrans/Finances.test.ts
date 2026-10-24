import { enableAutoUnmount, type VueWrapper } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { ErreurDepot } from '../../application/erreurs'
import { resumeFinances } from '../../test/fabriques'
import { fauxPorts } from '../../test/faux-ports'
import { monterEcran } from '../../test/monter'

const FINE = ' '
const xof = (texte: string) => texte.replace(/(\d) (?=\d)/g, `$1${FINE}`).replace(/ FCFA/g, `${FINE}FCFA`)
const net = (w: Pick<VueWrapper, 'text'>) => w.text().replace(/\s+/g, ' ').trim()

function afficher(resume = resumeFinances(), droits = { intendance: true, finances: true, pilotage: false }) {
  const ports = fauxPorts()
  ports.session.droits.mockReturnValue(droits)
  ports.intendance.resume.mockResolvedValue(resume)
  return monterEcran('/finances', ports)
}

enableAutoUnmount(afterEach)

describe('Finances', () => {
  it('trois indicateurs : encaissé du mois (évolution), recouvrement, retards dont bloqués', async () => {
    const { w } = await afficher()
    expect(document.title).toBe('Finances · OpenLab Academy')
    expect(w.find('h1').text()).toBe('Finances')
    const cartes = w.findAll('.indicateur')
    expect(cartes.map((c) => c.find('.libelle').text())).toEqual([
      'Encaissé ce mois',
      'Taux de recouvrement',
      'Apprenants en retard',
    ])
    expect(cartes[0]!.find('.valeur').text()).toBe(xof('155 000 FCFA'))
    expect(net(cartes[0]!.find('.detail'))).toBe('+12,5 % par rapport au mois dernier à date')
    expect(cartes[1]!.find('.valeur').text()).toBe(`73,8${FINE}%`)
    expect(cartes[2]!.find('.valeur').text()).toBe('3')
    expect(net(cartes[2]!.find('.detail'))).toBe('dont 2 bloqués')
  })

  it('tableau par parcours : inscrits, encaissé, reste dû', async () => {
    const { w } = await afficher()
    const lignes = w.findAll('.par-parcours tbody tr')
    expect(lignes).toHaveLength(2)
    expect(lignes[0]!.findAll('th, td').map((c) => c.text())).toEqual([
      'Fondamentaux de la data science',
      '3',
      xof('155 000 FCFA'),
      xof('145 000 FCFA'),
    ])
    expect(w.findAll('.par-parcours tfoot th, .par-parcours tfoot td').map((c) => c.text())).toEqual([
      'Total',
      '4',
      xof('155 000 FCFA'),
      xof('265 000 FCFA'),
    ])
  })

  it('répartition des modes en texte et dernières actions de l’équipe', async () => {
    const { w } = await afficher()
    expect(w.findAll('.modes li').map((l) => net(l))).toEqual([
      'En une fois : 1 (25 %)',
      'En deux tranches : 2 (50 %)',
      'Chaque mois : 1 (25 %)',
    ])
    const action = w.find('.actions li')
    expect(action.find('.acteur').text()).toBe('intendant@openlab.ci')
    expect(action.find('.action').text()).toBe('Délai accordé')
    expect(action.find('.motif').text()).toBe('Accord avec la famille')
    // apprenant et parcours nommés, jamais l'identifiant technique du dossier
    expect(net(action.find('.concerne'))).toBe('Yao Bamba · Python avancé')
    expect(action.text()).not.toContain('DP-0002')
    expect(action.find('time').attributes('datetime')).toBe('2026-11-02T10:00:00Z')
  })

  it('accès aux prix et à l’enregistrement d’un virement', async () => {
    const { w } = await afficher()
    expect(w.find('a.prix').attributes('href')).toBe('/app/tarif-parcours-openlab')
    expect(w.find('a.virement').attributes('href')).toBe('/intendance')
    expect(w.find('a.virement').text()).toBe('Ouvrir l’Intendance')
    expect(w.find('.acces .petit').text()).toContain('depuis la fiche de l’apprenant')
  })

  it('sans base : évolution et taux non calculés, aucun inscrit', async () => {
    const { w } = await afficher(
      resumeFinances({
        evolution_pct: null,
        taux_recouvrement: null,
        par_parcours: [],
        modes: { une_fois: 0, deux_tranches: 0, mensuel: 0 },
        dernieres_actions: [],
        bloques: 0,
      }),
    )
    const cartes = w.findAll('.indicateur')
    expect(net(cartes[0]!.find('.detail'))).toBe('Pas de comparaison possible avec le mois dernier')
    expect(cartes[1]!.find('.valeur').text()).toBe('—')
    expect(cartes[2]!.find('.detail').exists()).toBe(false)
    expect(w.find('.par-parcours').exists()).toBe(false)
    expect(w.find('.aucun-parcours').text()).toBe('Aucun dossier de paiement pour le moment.')
    expect(w.findAll('.modes li').map((l) => net(l))[0]).toBe('En une fois : 0 (0 %)')
    expect(w.find('.aucune-action').text()).toBe('Aucune action pour le moment.')
  })

  it('évolution négative écrite avec son signe', async () => {
    const { w } = await afficher(resumeFinances({ evolution_pct: -8 }))
    expect(net(w.find('.indicateur .detail'))).toBe('−8 % par rapport au mois dernier à date')
  })

  it('réservé à l’administration : aucun appel sans le droit ; refus du serveur affiché', async () => {
    const sans = await afficher(resumeFinances(), { intendance: true, finances: false, pilotage: false })
    expect(sans.w.find('.reserve').text()).toContain('réservé à l’administration')
    expect(sans.ports.intendance.resume).not.toHaveBeenCalled()
    sans.w.unmount()
    const ports = fauxPorts()
    ports.session.droits.mockReturnValue({ intendance: true, finances: true, pilotage: false })
    ports.intendance.resume.mockRejectedValue(new ErreurDepot('hors_ligne'))
    const { w } = await monterEcran('/finances', ports)
    expect(w.find('[role="alert"]').text()).toBe('Le serveur ne répond pas. Vérifiez votre connexion puis réessayez.')
  })
})

describe('liens de l’accueil selon les droits', () => {
  it('apprenant : aucun lien d’agent ; intendant : Intendance ; administrateur : les deux ; responsable : Pilotage', async () => {
    const liens = async (droits: { intendance: boolean; finances: boolean; pilotage: boolean }) => {
      const ports = fauxPorts()
      ports.session.droits.mockReturnValue(droits)
      const { w } = await monterEcran('/', ports)
      const hrefs = w.findAll('.lien').map((a) => a.attributes('href'))
      w.unmount()
      return hrefs
    }
    expect(await liens({ intendance: false, finances: false, pilotage: false })).toEqual(['/relecture', '/correcteur'])
    expect(await liens({ intendance: true, finances: false, pilotage: false })).toEqual([
      '/relecture',
      '/correcteur',
      '/intendance',
    ])
    expect(await liens({ intendance: true, finances: true, pilotage: false })).toEqual([
      '/relecture',
      '/correcteur',
      '/intendance',
      '/finances',
    ])
    expect(await liens({ intendance: false, finances: false, pilotage: true })).toEqual([
      '/relecture',
      '/correcteur',
      '/pilotage',
    ])
  })
})
