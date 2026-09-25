import type { ReactNode } from 'react'

import ProgressBar from './ProgressBar'

/** صفّ ترتيب: رقم + اسم + قيمة + شريط تقدّم — لوحة الصدارة والتقارير. */
type Props = {
  rank: ReactNode
  name: ReactNode
  value: ReactNode
  pct: number
  sub?: ReactNode
  top?: boolean
}

export default function BarRow({ rank, name, value, pct, sub, top = false }: Props) {
  return (
    <div className="mb-3.5">
      <div className="mb-1.5 flex items-baseline gap-2">
        <bdi dir="ltr" className={`w-5 shrink-0 text-[13px] ${top ? 'text-(--color-accent)' : 'text-(--color-text-dim)'}`}>
          {rank}
        </bdi>
        <span className="min-w-0 flex-1 truncate text-[14px]">{name}</span>
        <bdi dir="ltr" className={`shrink-0 text-[14px] ${top ? 'text-(--color-accent)' : 'text-(--color-text)'}`}>
          {value}
        </bdi>
      </div>
      <ProgressBar pct={pct} glow={top} />
      {sub ? <div className="mt-1 text-[11px] text-(--color-text-dim)">{sub}</div> : null}
    </div>
  )
}
