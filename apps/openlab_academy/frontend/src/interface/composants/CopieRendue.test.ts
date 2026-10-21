import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import CopieRendue from './CopieRendue.vue'

const COPIE = 'Je reformulerais : **pourquoi** les ventes ont-elles baissé à Bouaké ?\n\n<script>alert(1)</script>'

describe('CopieRendue', () => {
  it('rend la copie assainie et surligne la citation du critère actif', async () => {
    const w = mount(CopieRendue, { props: { texte: COPIE, citation: 'pourquoi les ventes' } })
    expect(w.find('script').exists()).toBe(false)
    expect(w.text()).toContain('<script>alert(1)</script>')
    expect(
      w
        .findAll('mark.citation')
        .map((m) => m.element.textContent)
        .join(''),
    ).toBe('pourquoi les ventes')
    await w.setProps({ citation: 'baissé à Bouaké' })
    expect(
      w
        .findAll('mark.citation')
        .map((m) => m.element.textContent)
        .join(''),
    ).toBe('baissé à Bouaké')
    await w.setProps({ citation: '' })
    expect(w.find('mark').exists()).toBe(false)
  })

  it('une citation piégée reste du texte', () => {
    const w = mount(CopieRendue, {
      props: { texte: 'Texte <img src=x onerror=alert(1)> fin', citation: '<img src=x onerror=alert(1)>' },
    })
    expect(w.find('img').exists()).toBe(false)
    expect(w.find('mark').text()).toBe('<img src=x onerror=alert(1)>')
  })
})
