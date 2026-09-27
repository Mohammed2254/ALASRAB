/**
 * @covers ق-٢٤٥
 *
 * كل مسار في `FEED_ICONS` يقع داخل صندوق ٢٤×٢٤.
 *
 * **لماذا فحصٌ لا ثقة؟** لأن مسارًا بإحداثيات ٦٤ داخل صندوق ٢٤ يُرسَم خارج
 * الرؤية كليًّا **بلا أن يسقط شيء**: لا بناء ولا أنواع ولا قياس تباين ولا
 * أرضية لمس — يُرى بالعين وحدها. وقع مرّتين (`Deck` في و-١٦ ثم لوحة القيادة
 * في و-٢٠ رغم تعليقٍ صريح يحذّر منه). النوع يمنع **تمرير** مسارٍ غريب، وهذا
 * الفحص يمنع **إضافة** واحدٍ إلى الجدول نفسه.
 */
import { describe, expect, it } from 'vitest'

import { FEED_ICONS } from '../ui/feedIcons'

const VIEWBOX = 24

describe('أيقونات FeedRow داخل صندوقها', () => {
  it('حارس الفراغ: الجدول غير فارغ', () => {
    expect(Object.keys(FEED_ICONS).length).toBeGreaterThan(4)
  })

  it('لا إحداثيّ يتجاوز ٢٤ في أيّ مسار', () => {
    const offenders: string[] = []
    for (const [name, path] of Object.entries(FEED_ICONS)) {
      const numbers = [...path.matchAll(/-?\d+(?:\.\d+)?/g)].map((m) => Number(m[0]))
      const outside = numbers.filter((n) => n > VIEWBOX || n < -VIEWBOX)
      if (outside.length) offenders.push(`${name}: ${outside.join(', ')}`)
    }
    expect(offenders).toEqual([])
  })
})
