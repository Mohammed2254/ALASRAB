import type { ReactNode } from 'react'

/** صفّ بيانات داخل لوح: تسمية + قيمة (بلهجة لونية اختيارية) + نصّ فرعي. */
type Props = {
  label: ReactNode
  value: ReactNode
  tone?: 'accent' | 'red' | 'green' | undefined
  sub?: ReactNode
}

const TONE_CLASS: Record<NonNullable<Props['tone']>, string> = {
  accent: 'text-(--color-accent)',
  red: 'text-(--color-red-text)',
  green: 'text-(--color-green)',
}

export default function Prow({ label, value, tone, sub }: Props) {
  return (
    <div className="flex items-baseline justify-between gap-2.5 border-b border-(--color-border) py-2.5 last:border-none">
      <span className="shrink-0 text-[13px] text-(--color-text-dim)">{label}</span>
      <div className="text-left">
        <span className={`text-[13px] font-semibold ${tone ? TONE_CLASS[tone] : 'text-(--color-text)'}`}>
          {value}
        </span>
        {sub ? <div className="mt-0.5 text-[11px] text-(--color-text-dim)">{sub}</div> : null}
      </div>
    </div>
  )
}
