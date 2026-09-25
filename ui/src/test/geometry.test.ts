/**
 * @covers ق-٢٢٧
 *
 * كل دالّة في `motion/geometry.ts` مُختبَرة عند ٠٪ و١٠٠٪ وخارج المدى
 * (سالب/>١٠٠) — القيم منقولة حرفيًّا من النموذج المعتمد، والاختبار يثبّتها
 * رقميًّا لا وصفيًّا.
 */
import { describe, expect, it } from 'vitest'

import {
  chgDirection,
  formationPlaneSize,
  formationSkyHeight,
  fuelDialGeometry,
  progressScaleX,
} from '../motion/geometry'

describe('progressScaleX', () => {
  it('٠٪ ← ٠', () => {
    expect(progressScaleX(0)).toBe(0)
  })
  it('١٠٠٪ ← ١', () => {
    expect(progressScaleX(100)).toBe(1)
  })
  it('٤٢٪ ← ٠٫٤٢', () => {
    expect(progressScaleX(42)).toBeCloseTo(0.42)
  })
  it('سالب يُطوى إلى ٠ لا يُمرَّر سالبًا', () => {
    expect(progressScaleX(-10)).toBe(0)
  })
  it('فوق المائة يُطوى إلى ١', () => {
    expect(progressScaleX(140)).toBe(1)
  })
})

describe('fuelDialGeometry', () => {
  it('٠٪ ← أقصى إزاحة (قوس فارغ) وعقرب عند -٩٠°', () => {
    const g = fuelDialGeometry(0)
    expect(g.arcOffset).toBe(164)
    expect(g.needleDeg).toBe(-90)
  })
  it('١٠٠٪ ← صفر إزاحة (قوس ممتلئ) وعقرب عند +٩٠°', () => {
    const g = fuelDialGeometry(100)
    expect(g.arcOffset).toBe(0)
    expect(g.needleDeg).toBe(90)
  })
  it('٥٠٪ ← منتصف القوس ومنتصف مسح العقرب', () => {
    const g = fuelDialGeometry(50)
    expect(g.arcOffset).toBeCloseTo(82)
    expect(g.needleDeg).toBeCloseTo(0)
  })
  it('خارج المدى (سالب أو >١٠٠) يُطوى قبل الحساب لا يُمدَّد القوس/العقرب خارج المرسوم', () => {
    expect(fuelDialGeometry(-20)).toEqual(fuelDialGeometry(0))
    expect(fuelDialGeometry(250)).toEqual(fuelDialGeometry(100))
  })
})

describe('formationPlaneSize', () => {
  it('٠٪ ← ٢٦px (الحدّ الأدنى)', () => {
    expect(formationPlaneSize(0)).toBe(26)
  })
  it('١٠٠٪ ← ٥٢px (الحدّ الأقصى)', () => {
    expect(formationPlaneSize(100)).toBe(52)
  })
  it('طائرة أرضية (خارج المدى سالبًا) لا تصغر عن الحدّ الأدنى', () => {
    expect(formationPlaneSize(-5)).toBe(26)
  })
  it('تحصيل يفوق ١٠٠٪ (مثل قائد فوق العتبة القصوى) لا يكبر عن الحدّ الأقصى', () => {
    expect(formationPlaneSize(180)).toBe(52)
  })
})

describe('formationSkyHeight', () => {
  it('طائرة واحدة أو صفر ← ١١٠', () => {
    expect(formationSkyHeight(0)).toBe(110)
    expect(formationSkyHeight(1)).toBe(110)
  })
  it('طائرتان أو ثلاث ← ١٧٢', () => {
    expect(formationSkyHeight(2)).toBe(172)
    expect(formationSkyHeight(3)).toBe(172)
  })
  it('أربع فأكثر ← ٢١٠', () => {
    expect(formationSkyHeight(4)).toBe(210)
    expect(formationSkyHeight(9)).toBe(210)
  })
})

describe('chgDirection', () => {
  it('٠ ← same بمقدار صفر', () => {
    expect(chgDirection(0)).toEqual({ direction: 'same', magnitude: 0 })
  })
  it('موجب ← up بنفس المقدار', () => {
    expect(chgDirection(3)).toEqual({ direction: 'up', magnitude: 3 })
  })
  it('سالب ← down بمقدار موجب (لا سالبًا مضاعفًا)', () => {
    expect(chgDirection(-3)).toEqual({ direction: 'down', magnitude: 3 })
  })
})
