import { describe, expect, it } from 'vitest'
import { formaterDate, lienSur } from './dates'

describe('dates et liens', () => {
  it('formate une date Frappe en français', () => {
    expect(formaterDate('2026-11-03 21:12:00')).toMatch(/3 novembre/)
    expect(formaterDate('')).toBe('')
    expect(formaterDate(null)).toBe('')
    expect(formaterDate('pas une date')).toBe('')
  })

  it("n'accepte que les liens http(s)", () => {
    expect(lienSur('https://github.com/a/b')).toBe('https://github.com/a/b')
    expect(lienSur('HTTP://exemple.ci')).toBe('HTTP://exemple.ci')
    expect(lienSur('javascript:alert(1)')).toBe('')
    expect(lienSur('data:text/html,x')).toBe('')
    expect(lienSur(null)).toBe('')
  })
})
