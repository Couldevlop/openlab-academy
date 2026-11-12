import { enableAutoUnmount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { monterEcran } from '../../test/monter'

enableAutoUnmount(afterEach)

describe('retour à « Mon espace » depuis chaque écran', () => {
  it.each(['/correcteur', '/lots', '/relecture', '/retour/C1'])('%s', async (chemin) => {
    const { w } = await monterEcran(chemin)
    const lien = w.findAll('header a').find((a) => a.text() === 'Mon espace')
    expect(lien?.attributes('href')).toBe('/')
  })
})
