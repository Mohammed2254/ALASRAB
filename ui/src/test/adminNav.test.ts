/**
 * @covers ق-٢٤٣
 *
 * الجداول الثلاثة التي تقود لوحة المشرف تبقى متّفقة — بالفحص لا بالانتباه.
 *
 * المترجم يحرس اتّجاهين منهما: `AdminKey` يُلزم مفتاحَ كل عنصر في القائمة،
 * و`Record<AdminKey, …>` يُلزم سجلَّ الشاشات فمسارٌ بلا شاشة يُسقط `tsc`.
 * **والاتّجاه الثالث لا يحرسه المترجم:** مسارٌ لا تذكره القائمة الجانبية يبقى
 * صحيحَ الأنواع تمامًا ويصير شاشةً **لا طريق إليها** — وهو بعينه ما وقع في
 * و-١٧ حين سقط `adminDashboard` من التنقّل. فهذا الاختبار يحرسه.
 */
import { describe, expect, it } from 'vitest'

import { ADMIN_NAV, ADMIN_PATHS, isAdminScreen, LABEL_OF } from '../nav/adminNav'
import { ADMIN_SCREENS } from '../screens/admin/registry'
import { keyOf, pathOf, ROUTES } from '../nav/routes'

const navKeys = ADMIN_NAV.flatMap((group) => group.items.map((item) => item.key))

describe('اتّفاق جداول تنقّل المشرف', () => {
  it('القائمة الجانبية تغطّي كل مسارٍ إداريّ **مرّةً واحدة** — لا شاشة بلا طريق', () => {
    expect([...navKeys].sort()).toEqual(Object.keys(ADMIN_PATHS).sort())
    expect(new Set(navKeys).size).toBe(navKeys.length)
  })

  it('سجلّ الشاشات يغطّي كل مسارٍ إداريّ', () => {
    expect(Object.keys(ADMIN_SCREENS).sort()).toEqual(Object.keys(ADMIN_PATHS).sort())
  })

  it('لكل مفتاحٍ تسميةٌ مشتقّة من القائمة نفسها', () => {
    expect(Object.keys(LABEL_OF).sort()).toEqual(Object.keys(ADMIN_PATHS).sort())
    for (const label of Object.values(LABEL_OF)) expect(label.trim()).not.toBe('')
  })

  it('`ROUTES` يركّب الطيّار والمشرف بلا فقدان ولا تصادم', () => {
    for (const [key, path] of Object.entries(ADMIN_PATHS)) {
      expect(ROUTES[key as keyof typeof ROUTES]).toBe(path)
    }
    // مسارات فريدة: مسارٌ مكرَّر يجعل `keyOf` يُرجع أحدهما عشوائيًّا.
    const paths = Object.values(ROUTES)
    expect(new Set(paths).size).toBe(paths.length)
  })

  it('كل مسارٍ إداريّ يعود إلى مفتاحه ذهابًا وعودة', () => {
    for (const key of navKeys) expect(keyOf(pathOf(key))).toBe(key)
  })

  /**
   * **خطأُ تسميةٍ عاش من و-١٨ إلى و-٢١:** كان `adminAudit` (سجلّ التدقيق)
   * مسمًّى «الصندوق الأسود»، و`SCOPE.md` يقول غيره في موضعين — `§٨` بند ١٣
   * «الصندوق الأسود (**ملاحظة مجهولة**)»، و`§٩` يعدّه من صفحات الطيّار،
   * أمّا «سجلّ التغييرات» فبند ١٥. والوثيقة تعلو الكود (`AGENTS.md`).
   *
   * ويُحرَس بالفحص لا بالتعليق: تسميةٌ تُعاد إلى الخطأ لا يُسقطها شيء آخر.
   */
  it('«الصندوق الأسود» هو الملاحظة المجهولة لا سجلّ التدقيق — `SCOPE.md §٨`', () => {
    expect(LABEL_OF.adminNotes).toBe('الصندوق الأسود')
    expect(LABEL_OF.adminAudit).toBe('سجلّ التغييرات')
  })

  it('`isAdminScreen` يميّز الإداريّ من شاشات الطيّار', () => {
    for (const key of navKeys) expect(isAdminScreen(key)).toBe(true)
    for (const key of ['deck', 'readings', 'station', 'formation', 'board', 'note']) {
      expect(isAdminScreen(key)).toBe(false)
    }
  })
})
