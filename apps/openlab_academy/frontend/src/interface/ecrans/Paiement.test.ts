import { enableAutoUnmount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { ErreurDepot } from '../../application/erreurs'
import { LIEN_REFUSE } from '../../application/paiement'
import { TELEPHONE_INVALIDE, type DossierPaiement } from '../../domaine/paiement'
import { dossierPaiement } from '../../test/fabriques'
import { fauxPorts, horlogeFixe } from '../../test/faux-ports'
import { monterEcran } from '../../test/monter'

const FINE = ' '
// montants écrits avec des espaces ordinaires dans les attentes, comparés avec les espaces fines de l'écran
const xof = (texte: string) => texte.replace(/(\d) (?=\d)/g, `$1${FINE}`).replace(/ FCFA/g, `${FINE}FCFA`)

async function afficher(d: DossierPaiement = dossierPaiement(), chemin = '/paiement/fondamentaux-data') {
  const ports = fauxPorts()
  ports.horloge = horlogeFixe(new Date('2026-11-02T09:00:00Z'))
  ports.paiement.monDossier.mockResolvedValue(d)
  return monterEcran(chemin, ports)
}

const texte = (w: VueWrapper, selecteur: string) =>
  w
    .find(selecteur)
    .text()
    .replace(/[ \t\r\n]+/g, ' ')

enableAutoUnmount(afterEach)

describe('Mes paiements', () => {
  it('dossier du parcours de l’adresse, titre de la page', async () => {
    const { w, ports } = await afficher()
    expect(ports.paiement.monDossier).toHaveBeenCalledWith('fondamentaux-data')
    expect(document.title).toBe('Mes paiements · OpenLab Academy')
    expect(w.find('h1').text()).toBe('Mes paiements')
    expect(w.find('.parcours').text()).toBe('Fondamentaux de la data science')
  })

  it('bandeau d’état : statut en toutes lettres, prochain versement et part réglée', async () => {
    const { w } = await afficher()
    expect(w.find('.statut').text()).toBe('À jour')
    expect(w.find('.montant-prochain').text()).toBe(xof('50 000 FCFA'))
    expect(w.find('.echeance-prochaine').text()).toContain('10 novembre 2026')
    const barre = w.find('[role="progressbar"]')
    expect(barre.attributes('aria-valuenow')).toBe('9')
    expect(barre.attributes('aria-valuetext')).toBe(xof('10 000 FCFA réglés sur 110 000 FCFA'))
  })

  it('en retard : dit en toutes lettres, pas seulement par la couleur', async () => {
    const { w } = await afficher(
      dossierPaiement({
        statut: 'en_retard',
        paye: 0,
        reste: 110000,
        echeances: [
          { date_limite: '2026-10-22', montant: 10000, libelle: "Frais d'inscription", couverte: false },
          { date_limite: '2026-11-02', montant: 50000, libelle: 'Échéance', couverte: false },
          { date_limite: '2026-12-10', montant: 50000, libelle: 'Échéance', couverte: false },
        ],
        prochaine: { date_limite: '2026-10-22', montant: 10000 },
      }),
    )
    expect(w.find('.statut').text()).toBe('En retard')
    const etats = w.findAll('.echeancier li .etat').map((e) => e.text())
    expect(etats).toEqual(['En retard', 'À régler aujourd’hui', 'À venir'])
    expect(w.find('.suspendu').exists()).toBe(false)
    expect(w.find('.jauge span').exists()).toBe(false) // rien de réglé : jauge vide
  })

  it('apprenant bloqué : bandeau calme, parcours suspendu, autres parcours ouverts', async () => {
    const { w } = await afficher(dossierPaiement({ statut: 'en_retard', bloque: true }))
    const bandeau = texte(w, '.suspendu')
    expect(bandeau).toContain('L’accès à ce parcours est suspendu jusqu’au paiement')
    expect(bandeau).toContain('Vos autres parcours à jour restent ouverts.')
    expect(w.find('.suspendu').attributes('role')).toBe('status')
  })

  it('échéancier : chaque ligne datée, montant, état écrit, prochaine repérée', async () => {
    const { w } = await afficher()
    const lignes = w.findAll('.echeancier li')
    expect(lignes).toHaveLength(3)
    expect(lignes.map((l) => l.find('.etat').text())).toEqual(['Réglée', 'Prochaine', 'À venir'])
    expect(lignes[1]!.text()).toContain(xof('50 000 FCFA'))
    expect(lignes[1]!.text()).toContain('10 novembre 2026')
    expect(lignes[1]!.attributes('aria-current')).toBe('step')
  })

  it('trois modes en groupe radio, avec leur prix global et leur calendrier', async () => {
    const { w } = await afficher()
    const groupe = w.find('[role="radiogroup"]')
    expect(groupe.attributes('aria-labelledby')).toBeTruthy()
    const cartes = groupe.findAll('.mode')
    expect(cartes.map((c) => c.find('.mode-prix').text())).toEqual([
      xof('100 000 FCFA'),
      xof('110 000 FCFA'),
      xof('120 000 FCFA'),
    ])
    expect(cartes.map((c) => c.find('.mode-nom').text())).toEqual(['En une fois', 'En deux tranches', 'Chaque mois'])
    expect(cartes[2]!.find('.mode-calendrier').text()).toBe('Un versement par mois jusqu’à la fin du parcours')
    const radios = groupe.findAll<HTMLInputElement>('input[type="radio"]')
    expect(radios.map((r) => r.element.checked)).toEqual([false, true, false])
    expect(cartes[1]!.text()).toContain('Mode actuel')
    expect(texte(w, '.frais')).toContain(xof('10 000 FCFA'))
  })

  it('changer de mode : confirmation (nouveau prix, déjà versé, reste), appel, puis échéancier rafraîchi', async () => {
    const { w, ports } = await afficher()
    const apres = dossierPaiement({
      mode: 'mensuel',
      reste: 110000,
      echeances: [
        { date_limite: '2026-10-22', montant: 10000, libelle: 'Déjà versé', couverte: true },
        { date_limite: '2026-11-10', montant: 55000, libelle: 'Échéance', couverte: false },
        { date_limite: '2026-12-10', montant: 55000, libelle: 'Échéance', couverte: false },
      ],
      prochaine: { date_limite: '2026-11-10', montant: 55000 },
    })
    ports.paiement.choisirMode.mockResolvedValue(apres)
    await w.find('input[value="mensuel"]').setValue(true)
    await w.find('.enregistrer').trigger('click')
    expect(ports.paiement.choisirMode).not.toHaveBeenCalled()
    expect(w.find('.confirmation h3').text()).toBe(`Passer au paiement chaque mois${FINE}?`)
    expect(w.findAll('.confirmation dl > div').map((l) => [l.find('dt').text(), l.find('dd').text()])).toEqual([
      ['Nouveau prix global', xof('120 000 FCFA')],
      ['Déjà versé', xof('10 000 FCFA')],
      ['Reste à payer', xof('110 000 FCFA')],
    ])
    expect(document.activeElement).toBe(w.find('.confirmation h3').element)
    await w.find('.confirmer').trigger('click')
    await flushPromises()
    expect(ports.paiement.choisirMode).toHaveBeenCalledWith('fondamentaux-data', 'mensuel', '+2250700000001')
    expect(w.find('.confirmation').exists()).toBe(false)
    expect(w.findAll('.echeancier li').map((l) => l.find('.montant').text())).toEqual([
      xof('10 000 FCFA'),
      xof('55 000 FCFA'),
      xof('55 000 FCFA'),
    ])
    expect(w.find('.montant-prochain').text()).toBe(xof('55 000 FCFA'))
    expect(w.find('.succes').text()).toBe('Mode enregistré : votre échéancier est à jour.')
  })

  it('annuler la confirmation : rien n’est envoyé', async () => {
    const { w, ports } = await afficher()
    await w.find('input[value="une_fois"]').setValue(true)
    await w.find('.enregistrer').trigger('click')
    await w.find('.annuler').trigger('click')
    expect(w.find('.confirmation').exists()).toBe(false)
    expect(ports.paiement.choisirMode).not.toHaveBeenCalled()
    expect(document.activeElement).toBe(w.find('.enregistrer').element)
  })

  it('téléphone invalide : erreur sous le champ, aucun envoi', async () => {
    const { w, ports } = await afficher(dossierPaiement({ telephone: '' }))
    await w.find('input[type="tel"]').setValue('0700')
    await w.find('.enregistrer').trigger('click')
    const champ = w.find('input[type="tel"]')
    expect(champ.attributes('aria-invalid')).toBe('true')
    expect(w.find(`#${champ.attributes('aria-describedby')!.split(' ').pop()!}`).text()).toBe(TELEPHONE_INVALIDE)
    expect(w.find('.confirmation').exists()).toBe(false)
    expect(document.activeElement).toBe(champ.element)
    expect(ports.paiement.choisirMode).not.toHaveBeenCalled()
    await champ.setValue('+225 05 01 02 03 04')
    expect(champ.attributes('aria-invalid')).toBe('false')
  })

  it('téléphone vérifié en quittant le champ, pas pendant la frappe', async () => {
    const { w } = await afficher(dossierPaiement({ telephone: '' }))
    const champ = w.find('input[type="tel"]')
    await champ.trigger('blur')
    expect(champ.attributes('aria-invalid')).toBe('false')
    await champ.setValue('07 00')
    expect(champ.attributes('aria-invalid')).toBe('false')
    await champ.trigger('blur')
    expect(champ.attributes('aria-invalid')).toBe('true')
  })

  it('refus du serveur au changement de mode : message clair', async () => {
    const { w, ports } = await afficher()
    ports.paiement.choisirMode.mockRejectedValue(new ErreurDepot('trop_de_demandes'))
    await w.find('input[value="mensuel"]').setValue(true)
    await w.find('.enregistrer').trigger('click')
    await w.find('.confirmer').trigger('click')
    await flushPromises()
    expect(w.find('.modes [role="alert"]').text()).toContain('Trop de demandes')
    expect(w.findAll('.echeancier li')).toHaveLength(3)
  })

  it('payer : redirection vers la page de paiement rendue par le serveur', async () => {
    const { w, ports } = await afficher()
    ports.paiement.payer.mockResolvedValue('https://checkout.cinetpay.com/payment/abc')
    const bouton = w.find('.payer')
    expect(bouton.text()).toBe(xof('Payer 50 000 FCFA'))
    await bouton.trigger('click')
    await flushPromises()
    expect(ports.paiement.payer).toHaveBeenCalledWith('fondamentaux-data')
    expect(ports.navigateur.aller).toHaveBeenCalledWith('https://checkout.cinetpay.com/payment/abc')
  })

  it('payer : lien douteux jamais suivi, erreur affichée', async () => {
    const { w, ports } = await afficher()
    ports.paiement.payer.mockResolvedValue('http://pirate.example/pay')
    await w.find('.payer').trigger('click')
    await flushPromises()
    expect(ports.navigateur.aller).not.toHaveBeenCalled()
    expect(w.find('.releve [role="alert"]').text()).toBe(LIEN_REFUSE)
    expect(w.find('.payer').attributes('disabled')).toBeUndefined()
  })

  it('paiement en ligne non configuré : instructions de virement en texte brut, bientôt disponible', async () => {
    const piege = '<img src=x onerror=alert(1)>\nBanque Atlantique — IBAN CI93 0000'
    const { w } = await afficher(dossierPaiement({ paiement_en_ligne: false, instructions_virement: piege }))
    expect(w.find('.payer').exists()).toBe(false)
    expect(texte(w, '.releve')).toContain('Paiement en ligne bientôt disponible')
    expect(w.find('.releve a[href="#virement"]').exists()).toBe(true)
    expect(w.find('#virement .instructions').text()).toBe(piege)
    expect(w.findAll('img').map((i) => i.attributes('src'))).toEqual(['/assets/openlab_academy/images/logo-email.png'])
  })

  it('virement sans instructions saisies : l’intendance est indiquée', async () => {
    const { w } = await afficher(dossierPaiement({ paiement_en_ligne: false }))
    expect(texte(w, '#virement')).toContain('Les coordonnées de virement vous sont communiquées par l’intendance')
  })

  it('paiement en ligne disponible et instructions saisies : le virement reste proposé', async () => {
    const { w } = await afficher(dossierPaiement({ instructions_virement: 'Banque X' }))
    expect(w.find('.payer').exists()).toBe(true)
    expect(w.find('#virement .instructions').text()).toBe('Banque X')
  })

  it('parcours soldé : rien à payer, choix du mode masqué', async () => {
    const { w } = await afficher(
      dossierPaiement({
        statut: 'solde',
        paye: 110000,
        reste: 0,
        prochaine: null,
        echeances: dossierPaiement().echeances.map((e) => ({ ...e, couverte: true })),
      }),
    )
    expect(w.find('.statut').text()).toBe('Soldé')
    expect(w.find('.payer').exists()).toBe(false)
    expect(texte(w, '.releve')).toContain('Votre parcours est entièrement réglé.')
    expect(w.find('.modes').exists()).toBe(false)
    expect(w.find('[role="progressbar"]').attributes('aria-valuenow')).toBe('100')
    expect(w.find('.jauge span').attributes('style')).toContain('width: 100%')
  })

  it('dispensé : aucun montant demandé', async () => {
    const { w } = await afficher(dossierPaiement({ statut: 'dispense', prochaine: null, paye: 0, reste: 0 }))
    expect(w.find('.statut').text()).toBe('Dispensé')
    expect(w.find('.jauge span').exists()).toBe(true)
    expect(texte(w, '.releve')).toContain('Vous êtes dispensé des frais de ce parcours.')
    expect(w.find('.modes').exists()).toBe(false)
  })

  it('prochain versement sans date (frais restants) : montant seul', async () => {
    const { w } = await afficher(dossierPaiement({ prochaine: { date_limite: null, montant: 10000 } }))
    expect(w.find('.echeance-prochaine').exists()).toBe(false)
    expect(w.find('.payer').text()).toBe(xof('Payer 10 000 FCFA'))
  })

  it('aucun dossier pour ce parcours : message dédié', async () => {
    const ports = fauxPorts()
    ports.paiement.monDossier.mockRejectedValue(new ErreurDepot('acces_refuse'))
    const { w } = await monterEcran('/paiement/inconnu', ports)
    expect(w.find('[role="alert"]').text()).toBe(
      'Aucun dossier de paiement pour ce parcours. Vérifiez le lien ou contactez l’intendance.',
    )
    expect(w.find('h1').text()).toBe('Mes paiements')
  })

  it('serveur injoignable : message de panne', async () => {
    const ports = fauxPorts()
    ports.paiement.monDossier.mockRejectedValue(new ErreurDepot('hors_ligne'))
    const { w } = await monterEcran('/paiement/C1', ports)
    expect(w.find('[role="alert"]').text()).toContain('Le serveur ne répond pas')
  })

  it('autre parcours dans l’adresse : le dossier est rechargé', async () => {
    const { routeur, ports } = await afficher()
    await routeur.push('/paiement/autre-parcours')
    await flushPromises()
    expect(ports.paiement.monDossier).toHaveBeenLastCalledWith('autre-parcours')
  })
})
