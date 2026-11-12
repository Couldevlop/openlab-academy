import { enableAutoUnmount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { ErreurDepot } from '../../application/erreurs'
import { ficheIntendance, ligneIntendance, vueIntendance } from '../../test/fabriques'
import { fauxPorts, horlogeFixe, type FauxPorts } from '../../test/faux-ports'
import { monterEcran } from '../../test/monter'

const FINE = ' '
const xof = (texte: string) => texte.replace(/(\d) (?=\d)/g, `$1${FINE}`).replace(/ FCFA/g, `${FINE}FCFA`)
const net = (w: VueWrapper | ReturnType<VueWrapper['find']>) => w.text().replace(/\s+/g, ' ').trim()

function portsAgent(droits = { intendance: true, finances: false, pilotage: false }): FauxPorts {
  const ports = fauxPorts()
  ports.horloge = horlogeFixe(new Date('2026-11-02T09:00:00Z'))
  ports.session.droits.mockReturnValue(droits)
  ports.intendance.intendance.mockResolvedValue(vueIntendance())
  ports.intendance.fiche.mockResolvedValue(ficheIntendance())
  return ports
}

async function afficher(ports = portsAgent()) {
  return monterEcran('/intendance', ports)
}

async function ouvrirFiche(w: VueWrapper, rang = 0) {
  await w.findAll('.ouvrir')[rang]!.trigger('click')
  await flushPromises()
}

enableAutoUnmount(afterEach)

describe('Intendance', () => {
  it('titre, indicateurs en cartes et lignes du serveur', async () => {
    const { w, ports } = await afficher()
    expect(document.title).toBe('Intendance · OpenLab Academy')
    expect(w.find('h1').text()).toBe('Intendance')
    expect(ports.intendance.intendance).toHaveBeenCalledWith({})
    const cartes = w.findAll('.indicateur')
    expect(cartes.map((c) => c.find('.libelle').text())).toEqual([
      'Encaissé ce mois',
      'À échoir sous 30 jours',
      'En retard',
      'Comptes bloqués',
    ])
    expect(cartes[0]!.find('.valeur').text()).toBe(xof('155 000 FCFA'))
    expect(net(cartes[2]!)).toContain('1 apprenant')
    expect(cartes[3]!.find('.valeur').text()).toBe('1')
    expect(w.findAll('tbody tr')).toHaveLength(2)
  })

  it('statut écrit en toutes lettres (jamais la couleur seule) : à jour, rappel envoyé, bloqué, soldé', async () => {
    const ports = portsAgent()
    ports.intendance.intendance.mockResolvedValue(
      vueIntendance({
        lignes: [
          ligneIntendance({ dossier: 'A' }),
          ligneIntendance({ dossier: 'B', rappel_envoye: true }),
          ligneIntendance({ dossier: 'C', statut: 'en_retard', bloque: true }),
          ligneIntendance({ dossier: 'D', statut: 'solde', prochaine: null, reste: 0 }),
          ligneIntendance({ dossier: 'E', statut: 'en_retard' }),
          ligneIntendance({ dossier: 'F', statut: 'dispense', prochaine: null, reste: 0 }),
        ],
      }),
    )
    const { w } = await afficher(ports)
    expect(w.findAll('tbody .puce-statut').map((p) => p.text())).toEqual([
      'À jour',
      'Rappel envoyé',
      'Bloqué',
      'Soldé',
      'En retard',
      'Dispensé',
    ])
  })

  it('filtres appliqués à l’API, lien d’export avec les mêmes filtres', async () => {
    const { w, ports } = await afficher()
    ports.intendance.lienExport.mockImplementation((f) => `/export?${new URLSearchParams(f).toString()}`)
    await w.find('select[name="parcours"]').setValue('python-avance')
    await w.find('select[name="mode"]').setValue('mensuel')
    await w.find('select[name="statut"]').setValue('en_retard')
    await w.find('input[name="du"]').setValue('2026-10-01')
    await w.find('input[name="au"]').setValue('2026-10-31')
    await w.find('form.filtres').trigger('submit')
    await flushPromises()
    expect(ports.intendance.intendance).toHaveBeenLastCalledWith({
      parcours: 'python-avance',
      mode: 'mensuel',
      statut: 'en_retard',
      du: '2026-10-01',
      au: '2026-10-31',
    })
    expect(w.findAll('select[name="statut"] option').map((o) => o.text())).toContain('Bloqué')
    expect(w.findAll('select[name="cohorte"] option').map((o) => o.text())).toEqual([
      'Toutes les cohortes',
      'Data, octobre 2026',
      'Python, septembre 2026',
    ])
    expect(w.find('a.export').attributes('href')).toBe(
      '/export?parcours=python-avance&mode=mensuel&statut=en_retard&du=2026-10-01&au=2026-10-31',
    )
    // parcours et cohortes proposés : ceux déjà vus, gardés quand le filtre réduit la liste
    expect(w.findAll('select[name="parcours"] option').map((o) => o.text())).toEqual([
      'Tous les parcours',
      'Fondamentaux de la data science',
      'Python avancé',
    ])
    await w.find('button.effacer').trigger('click')
    await flushPromises()
    expect(ports.intendance.intendance).toHaveBeenLastCalledWith({})
  })

  it('statut « Bloqué » filtré par le serveur ; cohorte affichée par son titre', async () => {
    const { w, ports } = await afficher()
    expect(w.find('tbody tr').text()).toContain('Data, octobre 2026')
    expect(w.find('tbody tr').text()).not.toContain('data-2026-10')
    await w.find('select[name="statut"]').setValue('bloque')
    await w.find('form.filtres').trigger('submit')
    await flushPromises()
    expect(ports.intendance.intendance).toHaveBeenLastCalledWith({ statut: 'bloque' })
  })

  it('filtre refusé par le serveur : message en texte', async () => {
    const { w, ports } = await afficher()
    ports.intendance.intendance.mockRejectedValue(new ErreurDepot('refus', ['La période est invalide.']))
    await w.find('form.filtres').trigger('submit')
    await flushPromises()
    expect(w.find('[role="alert"]').text()).toBe('La période est invalide.')
  })

  it('tri par colonne, annoncé par aria-sort', async () => {
    const { w } = await afficher()
    const noms = () => w.findAll('tbody .nom').map((n) => n.text())
    expect(noms()).toEqual(['Awa Koné', 'Yao Bamba'])
    await w.find('th[data-cle="etat"] button').trigger('click')
    expect(noms()).toEqual(['Yao Bamba', 'Awa Koné'])
    expect(w.find('th[data-cle="etat"]').attributes('aria-sort')).toBe('ascending')
    await w.find('th[data-cle="etat"] button').trigger('click')
    expect(w.find('th[data-cle="etat"]').attributes('aria-sort')).toBe('descending')
    expect(noms()).toEqual(['Awa Koné', 'Yao Bamba'])
  })

  it('tri sur mobile par une liste déroulante', async () => {
    const { w } = await afficher()
    const noms = () => w.findAll('tbody .nom').map((n) => n.text())
    await w.find('#tri-mobile').setValue('etat:asc')
    expect(noms()).toEqual(['Yao Bamba', 'Awa Koné'])
    expect(w.find('th[data-cle="etat"]').attributes('aria-sort')).toBe('ascending')
    await w.find('#tri-mobile').setValue('')
    expect(noms()).toEqual(['Awa Koné', 'Yao Bamba'])
  })

  it('liste tronquée et liste vide annoncées', async () => {
    const ports = portsAgent()
    ports.intendance.intendance.mockResolvedValue(vueIntendance({ tronque: true }))
    const { w } = await afficher(ports)
    expect(w.find('.tronque').text()).toContain('Affinez les filtres')
    ports.intendance.intendance.mockResolvedValue(vueIntendance({ lignes: [] }))
    await w.find('form.filtres').trigger('submit')
    await flushPromises()
    expect(w.find('.vide').text()).toBe('Aucun dossier ne correspond à ces filtres.')
  })

  it('sans le rôle : écran réservé, aucun appel', async () => {
    const ports = portsAgent({ intendance: false, finances: false, pilotage: false })
    const { w } = await afficher(ports)
    expect(w.find('.reserve').text()).toContain('réservé à l’intendance')
    expect(ports.intendance.intendance).not.toHaveBeenCalled()
  })

  it('accès refusé par le serveur malgré le lien : message', async () => {
    const ports = portsAgent()
    ports.intendance.intendance.mockRejectedValue(new ErreurDepot('acces_refuse'))
    const { w } = await afficher(ports)
    expect(w.find('[role="alert"]').text()).toBe("Cet élément n'existe pas ou ne vous est pas ouvert.")
  })
})

describe('Fiche d’un dossier', () => {
  it('panneau latéral : identité, échéancier, paiements, rappels par canal', async () => {
    const { w, ports } = await afficher()
    await ouvrirFiche(w)
    expect(ports.intendance.fiche).toHaveBeenCalledWith('DP-0001')
    const fiche = w.find('[role="dialog"]')
    expect(fiche.attributes('aria-modal')).toBe('true')
    expect(fiche.find('h2').text()).toBe('Awa Koné')
    expect(document.activeElement).toBe(fiche.find('h2').element)
    expect(net(fiche.find('.identite'))).toContain('+225 07 00 00 00 01')
    expect(fiche.findAll('.echeancier li')).toHaveLength(3)
    expect(net(fiche.find('.paiements li'))).toContain('Virement')
    expect(net(fiche.find('.paiements li'))).toContain('VIR-2026-001')
    expect(net(fiche.find('.rappels li'))).toContain('SMS')
    expect(net(fiche.find('.rappels li'))).toContain('7 jours avant')
  })

  it('journal : acteur, action, date et motif', async () => {
    const { w } = await afficher()
    await ouvrirFiche(w)
    const entree = w.find('.journal li')
    expect(entree.find('.acteur').text()).toBe('intendant@openlab.ci')
    expect(entree.find('.action').text()).toBe('Virement enregistré')
    expect(entree.find('time').text()).toBe('22 oct. 2026, 09:12')
    expect(entree.find('time').attributes('datetime')).toBe('2026-10-22T09:12:00Z')
    expect(w.find('.identite').text()).toContain('Data, octobre 2026')
    expect(w.find('.identite').text()).not.toContain('data-2026-10')
    expect(entree.find('.motif').text()).toBe('Relevé du 22 octobre')
    expect(entree.findAll('.detail li').map((l) => l.text())).toEqual([
      '10 000 FCFA · réf. VIR-2210 · versé le 22 octobre 2026',
      'Payé : 0 FCFA → 10 000 FCFA',
      'Statut : En retard → À jour',
    ])
  })

  it('texte venu du serveur affiché tel quel, jamais interprété', async () => {
    const ports = portsAgent()
    ports.intendance.fiche.mockResolvedValue(
      ficheIntendance({
        journal: [{ ...ficheIntendance().journal[0]!, motif: '<img src=x onerror=alert(1)>' }],
      }),
    )
    const { w } = await afficher(ports)
    await ouvrirFiche(w)
    expect(w.find('.journal .motif').text()).toBe('<img src=x onerror=alert(1)>')
    expect(w.find('.journal img').exists()).toBe(false)
  })

  it('dossier dispensé : ni virement, ni délai, échéances sans retard ni « due aujourd’hui »', async () => {
    const ports = portsAgent()
    ports.intendance.fiche.mockResolvedValue(
      ficheIntendance({
        dispense: true,
        statut: 'dispense',
        reste: 0,
        prochaine: null,
        echeances: [
          { date_limite: '2026-10-22', montant: 10000, libelle: "Frais d'inscription", couverte: true },
          { date_limite: '2026-10-30', montant: 50000, libelle: 'Échéance', couverte: false },
          { date_limite: '2026-11-02', montant: 50000, libelle: 'Échéance', couverte: false },
        ],
      }),
    )
    const { w } = await afficher(ports)
    await ouvrirFiche(w)
    expect(w.find('[role="dialog"]').text()).toContain('Dossier dispensé de paiement.')
    expect(w.find('button.vers-virement').exists()).toBe(false)
    expect(w.find('button.vers-delai').exists()).toBe(false)
    const etats = w.findAll('.echeancier li')
    expect(etats.map((e) => e.find('.etat').text())).toEqual(['Réglée', 'Dispensée', 'Dispensée'])
    expect(etats.map((e) => e.classes().find((c) => c.startsWith('etat-')))).toEqual([
      'etat-reglee',
      'etat-dispensee',
      'etat-dispensee',
    ])
  })

  it('Échap ferme le panneau et rend le focus au bouton de la ligne', async () => {
    const { w } = await afficher()
    await ouvrirFiche(w)
    await w.find('[role="dialog"]').trigger('keydown', { key: 'Escape' })
    await flushPromises()
    expect(w.find('[role="dialog"]').exists()).toBe(false)
    expect(document.activeElement).toBe(w.findAll('.ouvrir')[0]!.element)
  })

  it('le focus reste dans le panneau (Tab et Maj+Tab) ; Annuler referme le formulaire', async () => {
    const { w } = await afficher()
    await ouvrirFiche(w)
    const dialogue = w.find('[role="dialog"]')
    const focusables = dialogue.findAll('button')
    const dernier = focusables[focusables.length - 1]!
    ;(dernier.element as HTMLElement).focus()
    await dialogue.trigger('keydown', { key: 'Tab' })
    expect(document.activeElement).toBe(dialogue.find('button.fermer').element)
    await dialogue.trigger('keydown', { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(dernier.element)
    await w.find('button.vers-delai').trigger('click')
    expect(document.activeElement).toBe(w.find('input[name="jusquau"]').element)
    expect(w.find('input[name="jusquau"]').attributes('min')).toBe('2026-11-03')
    await w.findAll('form.delai button').at(-1)!.trigger('click')
    expect(w.find('form.delai').exists()).toBe(false)
  })

  it('Maj+Tab depuis le titre (focus à l’ouverture) reste dans le panneau', async () => {
    const { w } = await afficher()
    await ouvrirFiche(w)
    const dialogue = w.find('[role="dialog"]')
    expect(document.activeElement).toBe(dialogue.find('h2').element)
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', shiftKey: true, bubbles: true }))
    const boutons = dialogue.findAll('button')
    expect(document.activeElement).toBe(boutons[boutons.length - 1]!.element)
    ;(dialogue.find('h2').element as HTMLElement).focus()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true }))
    expect(document.activeElement).toBe(dialogue.find('button.fermer').element)
  })

  it('après un virement enregistré : focus sur le message, Tab piégé et Échap ferme encore', async () => {
    const { w } = await afficher()
    await ouvrirFiche(w)
    await w.find('button.vers-virement').trigger('click')
    const form = w.find('form.virement')
    await form.find('input[name="montant"]').setValue('50000')
    await form.find('input[name="reference"]').setValue('VIR-2026-003')
    await form.find('input[name="motif"]').setValue('Relevé')
    await form.trigger('submit')
    await flushPromises()
    const succes = w.find('.succes')
    expect(document.activeElement).toBe(succes.element)
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab', bubbles: true }))
    expect(w.find('[role="dialog"]').element.contains(document.activeElement)).toBe(true)
    document.body.focus()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await flushPromises()
    expect(w.find('[role="dialog"]').exists()).toBe(false)
    expect(document.activeElement).toBe(w.findAll('.ouvrir')[0]!.element)
  })

  it('fermeture : la ligne ayant disparu de la liste, le focus va au titre de la liste', async () => {
    const { w, ports } = await afficher()
    await ouvrirFiche(w)
    ports.intendance.intendance.mockResolvedValue(vueIntendance({ lignes: [] }))
    await w.find('button.vers-delai').trigger('click')
    await w.find('input[name="jusquau"]').setValue('2026-11-20')
    await w.find('textarea[name="motif"]').setValue('Accord')
    await w.find('form.delai').trigger('submit')
    await flushPromises()
    await w.find('button.fermer').trigger('click')
    await flushPromises()
    expect(document.activeElement).toBe(w.find('#titre-liste').element)
  })

  it('virement : montant vide et référence manquante refusés, sans appel', async () => {
    const { w, ports } = await afficher()
    await ouvrirFiche(w)
    await w.find('button.vers-virement').trigger('click')
    const form = w.find('form.virement')
    await form.find('input[name="motif"]').setValue('Relevé')
    await form.trigger('submit')
    await flushPromises()
    expect(form.find('#virement-montant-erreur').text()).toBe('Indiquez le montant reçu.')
    expect(form.find('#virement-reference-erreur').text()).toBe('Indiquez la référence du virement.')
    expect(form.find('input[name="montant"]').attributes('aria-invalid')).toBe('true')
    expect(document.activeElement).toBe(form.find('input[name="montant"]').element)
    expect(ports.intendance.enregistrerVirement).not.toHaveBeenCalled()
  })

  it('virement enregistré : envoi, message, liste et fiche rafraîchies', async () => {
    const { w, ports } = await afficher()
    await ouvrirFiche(w)
    await w.find('button.vers-virement').trigger('click')
    const form = w.find('form.virement')
    expect((form.find('input[name="date"]').element as HTMLInputElement).value).toBe('2026-11-02')
    await form.find('input[name="montant"]').setValue('50 000')
    await form.find('input[name="reference"]').setValue('VIR-2026-002')
    await form.find('input[name="motif"]').setValue('Relevé du 2 novembre')
    ports.intendance.fiche.mockResolvedValue(ficheIntendance({ paye: 60000 }))
    await form.trigger('submit')
    await flushPromises()
    expect(ports.intendance.enregistrerVirement).toHaveBeenCalledWith('DP-0001', {
      montant: 50000,
      reference: 'VIR-2026-002',
      date_paiement: '2026-11-02',
      motif: 'Relevé du 2 novembre',
    })
    expect(w.find('[role="status"].succes').text()).toBe('Virement enregistré.')
    expect(ports.intendance.intendance).toHaveBeenCalledTimes(2)
    expect(ports.intendance.fiche).toHaveBeenCalledTimes(2)
    expect(w.find('form.virement').exists()).toBe(false)
  })

  it('refus du serveur affiché en texte, saisie conservée', async () => {
    const { w, ports } = await afficher()
    await ouvrirFiche(w)
    await w.find('button.vers-virement').trigger('click')
    const form = w.find('form.virement')
    await form.find('input[name="montant"]').setValue('50000')
    await form.find('input[name="reference"]').setValue('VIR-2026-001')
    await form.find('input[name="motif"]').setValue('Relevé')
    ports.intendance.enregistrerVirement.mockRejectedValue(
      new ErreurDepot('refus', ['Cette référence de virement est déjà enregistrée.']),
    )
    await form.trigger('submit')
    await flushPromises()
    expect(w.find('form.virement [role="alert"]').text()).toBe('Cette référence de virement est déjà enregistrée.')
    expect((w.find('input[name="reference"]').element as HTMLInputElement).value).toBe('VIR-2026-001')
  })

  it('délai : échéance concernée, date après aujourd’hui et motif obligatoires, puis envoi', async () => {
    const { w, ports } = await afficher()
    await ouvrirFiche(w, 1)
    await w.find('button.vers-delai').trigger('click')
    const form = w.find('form.delai')
    expect(net(form.find('.concernee'))).toContain('50 000 FCFA')
    expect(net(form.find('.concernee'))).toContain('10 novembre 2026')
    await form.find('input[name="jusquau"]').setValue('2026-11-02')
    await form.trigger('submit')
    await flushPromises()
    expect(form.find('#delai-jusquau-erreur').text()).toBe('La nouvelle date limite doit être après aujourd’hui.')
    expect(form.find('#delai-motif-erreur').text()).toBe('Le motif est obligatoire.')
    expect(ports.intendance.accorderDelai).not.toHaveBeenCalled()
    await form.find('input[name="jusquau"]').setValue('2026-11-20')
    await form.find('textarea[name="motif"]').setValue('Accord avec la famille')
    await form.trigger('submit')
    await flushPromises()
    expect(ports.intendance.accorderDelai).toHaveBeenCalledWith('DP-0001', '2026-11-20', 'Accord avec la famille')
    expect(w.find('[role="status"].succes').text()).toBe('Délai enregistré.')
  })

  it('dossier soldé : rien à décaler ; fiche introuvable : message', async () => {
    const ports = portsAgent()
    ports.intendance.fiche.mockResolvedValue(
      ficheIntendance({
        statut: 'solde',
        reste: 0,
        prochaine: null,
        echeances: [{ date_limite: '2026-10-22', montant: 110000, libelle: 'Une fois', couverte: true }],
        delai_jusqu_au: '2026-11-20',
        rappels: [],
        paiements: [],
        journal: [],
      }),
    )
    const { w } = await afficher(ports)
    await ouvrirFiche(w)
    expect(w.find('button.vers-delai').exists()).toBe(false)
    expect(net(w.find('.delai-en-cours'))).toContain('20 novembre 2026')
    expect(w.find('.rappels .discret').text()).toBe('Aucun rappel envoyé.')
    await w.find('button.fermer').trigger('click')
    ports.intendance.fiche.mockRejectedValue(new ErreurDepot('acces_refuse'))
    await ouvrirFiche(w)
    expect(w.find('[role="dialog"] [role="alert"]').text()).toBe("Cet élément n'existe pas ou ne vous est pas ouvert.")
  })
})
