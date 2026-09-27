import type { ReactNode } from 'react'

/**
 * صفّ «بحاجة إلى إجراء منك» — تسمية + عدّاد + زرّ.
 *
 * **ولماذا ملفٌّ جديد لا شقٌّ في `Prow`؟** `Prow` بـ`items-baseline` في نحو
 * عشرين موضعًا، وزرٌّ بأرضية لمسٍ ٤٤px في صفّ خطّ قاعدة إمّا يبدو مائلًا أو
 * يُجبر شرطًا يُهدّد تلك المواضع كلّها. وهذا صفٌّ **نداءٌ إلى عمل** لا
 * معلومةٌ معروضة — اختلافُ الوظيفة يسبق اختلاف الشكل.
 */
type Props = { label: ReactNode; count: ReactNode; action: ReactNode }

export default function TaskRow({ label, count, action }: Props) {
  return (
    <div className="flex min-w-0 items-center gap-3 border-b border-(--color-border) py-2.5 last:border-none">
      <span className="min-w-0 flex-1 text-[13px]">{label}</span>
      <span className="num shrink-0 text-[15px] font-bold text-(--color-accent)">{count}</span>
      <span className="shrink-0">{action}</span>
    </div>
  )
}
