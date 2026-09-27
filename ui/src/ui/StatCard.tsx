import { useEffect, useRef } from 'react'

import type { Decimal } from '../api/brand'
import { countUp } from '../motion/mo'

/**
 * رقم كبير + تسمية — شبكة إحصائيات لوحة القيادة.
 *
 * `value` عشريٌّ نصّيّ **أو** رقم: بعض أرقام اللوحة عشريّة مُوسَمة (ADR-009)
 * وبعضها عدّاد صحيح، و`countUp` يقبل الاثنين أصلًا. و`decimals` يُمرَّر إليه
 * كما هو — لا تنسيق هنا.
 */
type Props = {
  value: Decimal | number
  label: string
  tone?: 'default' | 'accent' | 'danger'
  decimals?: 0 | 2
}

const TONE_CLASS: Record<NonNullable<Props['tone']>, string> = {
  default: 'text-(--color-text)',
  accent: 'text-(--color-accent)',
  danger: 'text-(--color-red-text)',
}

export default function StatCard({ value, label, tone = 'default', decimals = 0 }: Props) {
  const numRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    countUp(numRef.current, value, { decimals })
  }, [value, decimals])

  return (
    <div className="rounded-(--radius-md) border border-(--color-border) bg-(--color-surface) p-4.5">
      <div ref={numRef} className={`num mb-1.5 text-[32px] leading-none font-extrabold ${TONE_CLASS[tone]}`}>
        0
      </div>
      <div className="text-[12px] text-(--color-text-dim)">{label}</div>
    </div>
  )
}
