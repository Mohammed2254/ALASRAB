import { useEffect, useRef } from 'react'

import { countUp } from '../motion/mo'

/** رقم كبير + تسمية — شبكة إحصائيات لوحة القيادة. */
type Props = { value: number; label: string; tone?: 'default' | 'accent' | 'danger' }

const TONE_CLASS: Record<NonNullable<Props['tone']>, string> = {
  default: 'text-(--color-text)',
  accent: 'text-(--color-accent)',
  danger: 'text-(--color-red-text)',
}

export default function StatCard({ value, label, tone = 'default' }: Props) {
  const numRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    countUp(numRef.current, value)
  }, [value])

  return (
    <div className="rounded-(--radius-md) border border-(--color-border) bg-(--color-surface) p-4.5">
      <div ref={numRef} className={`num mb-1.5 text-[32px] leading-none font-extrabold ${TONE_CLASS[tone]}`}>
        0
      </div>
      <div className="text-[12px] text-(--color-text-dim)">{label}</div>
    </div>
  )
}
