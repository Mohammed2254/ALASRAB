/**
 * @covers ق-٢١٨
 *
 * إثبات أن الوسم العشريّ يعمل — **بأخطاء ترجمة متوقَّعة لا بتأكيدات وقت تشغيل**.
 *
 * `@ts-expect-error` يقلب المنطق: السطر يمرّ **لأن ما تحته خطأ**. فإن زال
 * المنع يومًا (حُذف الوسم، أو صار `Decimal = string`) تحوّل التعليق نفسه إلى
 * خطأ «توقَّعتُ خطأً ولم أجده» — فيسقط البناء. حارسٌ لا يمكن أن يصدأ بصمت.
 */

import { expectTypeOf } from 'vitest'

import { asDecimal, type Count, type Decimal, type Pct } from '../api/brand'
import { fmtDecimal } from '../api/format'

const hours: Decimal = asDecimal('611.25')
const remaining: Decimal = asDecimal('288.75')
const progressPct: Pct = 42.2
const members: Count = 6

describe('الوسم العشريّ — ADR-009', () => {
  it('يمنع العملية الحسابية على قيمة عشرية', () => {
    // @ts-expect-error العشريّ نصّ: الطرح عليه خطأ ترجمة لا NaN صامت
    void (hours - remaining)
    // ولا تأكيد بعده: `@ts-expect-error` **هو** الإثبات — فإن زال المنع صار
    // التعليق نفسه خطأً («توقَّعتُ خطأً ولم أجده») فيسقط البناء.
  })

  it('يمنع تمرير عشريّ مكان رقم', () => {
    const takesNumber = (n: Pct) => n
    // @ts-expect-error نسبةٌ تتوقّع رقمًا، والعشريّ نصّ موسوم
    takesNumber(hours)
    expectTypeOf(takesNumber(progressPct)).toBeNumber()
  })

  it('يمنع عودة ناتج Number إلى موضع عشريّ', () => {
    const asPlainNumber = Number(hours)
    const takesDecimal = (d: Decimal) => d
    // @ts-expect-error الوسم يرفض الرقم — فلا دورة ذهاب وإياب صامتة
    takesDecimal(asPlainNumber)
  })

  it('يمنع تمرير نصّ عاديّ مكان عشريّ — الوسم لا الشكل', () => {
    const takesDecimal = (d: Decimal) => d
    // @ts-expect-error `string` عاديّ ليس Decimal ولو بدا رقمًا
    takesDecimal('611.25')
    expectTypeOf(takesDecimal(hours)).toEqualTypeOf<Decimal>()
  })

  it('يمنع تنسيق نسبة رقمية كأنها عشريّ', () => {
    // @ts-expect-error `fmtDecimal` للعشريّ وحده — والنسبة رقم
    fmtDecimal(progressPct)
    expectTypeOf(fmtDecimal(hours)).toBeString()
  })

  it('يسمح بالعدّ الصحيح في الحساب — فالمنع مقصور على العشريّ', () => {
    expectTypeOf(members + 1).toBeNumber()
  })
})
