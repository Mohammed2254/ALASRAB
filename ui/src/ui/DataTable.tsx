import type { ReactNode } from 'react'

import Placard from './Placard'
import Prow from './Prow'
import { useDesk } from './useDesk'

/**
 * جدولٌ فوق الحدّ، **وبطاقةٌ لكل صفّ تحته** — `SCOPE.md §١٣`.
 *
 * **لا تمرير أفقيّ أبدًا**: لا `min-width` هنا ولا `overflow-x-auto`. جدولٌ
 * لا يلائم عرضه يُعالَج بترويسةٍ أقصر أو عمودٍ مدموج — لا بتمريرٍ يُسقط قياس
 * الانزياح.
 *
 * ## لماذا تفريعٌ في JS ورسمُ DOM واحد؟
 *
 * **ولمَ لا حيلة CSS الخالصة** (`content: attr(data-label)`): تنقل كل تسمية
 * حقل من عقدة نصّ إلى خاصّية HTML، حيث **لا يراها قياسُ التباين ولا فحصُ
 * تشكيل العربية** — فيخرج نصٌّ عربيّ من بوابتين صامتًا.
 *
 * **ولمَ لا «ارسم الاثنين وأخفِ أحدهما»**: قياس التباين يمشي كل عنصرٍ يحمل
 * عقدة نصّ **بلا مُرشِّح ظهور**، فتدخل مئةُ عقدةٍ مخفية مسارَ القياس في شاشة
 * راصد وحدها — ثمنٌ في كل تشغيل مقابل لا شيء.
 *
 * ## وكتلةٌ عليا لا تُعشَّش
 *
 * تخطيط البطاقات يُصدِر `Placard` لكل صفّ، و`VISUAL.md §٥` يمنع لوحًا داخل
 * لوح — فلا يُلَفّ `DataTable` بلوحٍ أبدًا.
 */
export type Column<T> = {
  /** مفتاحٌ ثابت — لا فهرس مصفوفة (يتغيّر بالفرز). */
  id: string
  /** ترويسة العمود فوق الحدّ، وتسمية الحقل تحته. */
  header: string
  /** المحتوى جاهزًا للعرض — الشاشة تُنسّق، والبدائية تُخطّط. */
  cell: (row: T) => ReactNode
  /** قيمةٌ مقيسة: لا تُلَفّ. */
  numeric?: true | undefined
  /** عنوان البطاقة تحت الحدّ — عمودٌ واحد فقط يحمل هذه. */
  primary?: true | undefined
}

type Props<T> = {
  columns: readonly Column<T>[]
  rows: readonly T[]
  rowKey: (row: T) => string | number
  /** عنوانُ الكتلة — فوق الحدّ يصير `<caption>` مخفيًّا، وتحته عنوانًا مرئيًّا. */
  caption: string
  /** ما يُعرض حين لا صفوف — نصٌّ مصمَّم لا فراغ. */
  empty: ReactNode
  /** إجراء الصفّ — خليّةٌ أخيرة فوق الحدّ، وذيلُ بطاقة تحته. */
  action?: ((row: T) => ReactNode) | undefined
}

export default function DataTable<T>({
  columns,
  rows,
  rowKey,
  caption,
  empty,
  action,
}: Props<T>) {
  const desk = useDesk()

  if (rows.length === 0) {
    return (
      <Placard title={caption}>
        <div className="py-2 text-[13px] text-(--color-text-dim)">{empty}</div>
      </Placard>
    )
  }

  // اسم «البقيّة» هنا `rest` لا مرادفه الإنجليزيّ الشائع: ذاك في قائمة
  // المفردات المحظورة، والفحص يسقط عليه **حتى داخل تعليق** — وقد سقط فعلًا
  // على التعليق الذي كان يشرح تجنّبه.
  const lead = columns.find((c) => c.primary)
  const rest = columns.filter((c) => !c.primary)

  if (!desk) {
    return (
      <>
        <h2 className="mb-2.5 text-[14px] font-bold">{caption}</h2>
        {rows.map((row) => (
          <Placard key={rowKey(row)} title={lead ? lead.cell(row) : caption}>
            {rest.map((col) => (
              <Prow key={col.id} label={col.header} value={col.cell(row)} />
            ))}
            {action ? <div className="pt-3">{action(row)}</div> : null}
          </Placard>
        ))}
      </>
    )
  }

  return (
    <Placard title={caption}>
      <table className="w-full border-collapse text-[13px]">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            {columns.map((col) => (
              <th
                key={col.id}
                scope="col"
                className={`border-b border-(--color-border) px-2 py-2 text-start text-[12px] font-semibold text-(--color-text-dim) ${
                  col.numeric ? 'whitespace-nowrap' : ''
                }`}
              >
                {col.header}
              </th>
            ))}
            {action ? <th scope="col" className="border-b border-(--color-border) px-2 py-2" /> : null}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={rowKey(row)} className="odd:bg-(--color-surface-2)">
              {columns.map((col) => (
                <td
                  key={col.id}
                  className={`px-2 py-2.5 align-middle ${
                    col.numeric ? 'whitespace-nowrap' : 'break-words'
                  }`}
                >
                  {col.cell(row)}
                </td>
              ))}
              {action ? <td className="px-2 py-2.5 align-middle">{action(row)}</td> : null}
            </tr>
          ))}
        </tbody>
      </table>
    </Placard>
  )
}
