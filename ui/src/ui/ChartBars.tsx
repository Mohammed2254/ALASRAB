import { useEnter } from '../motion/useEnter'

/** أعمدة يومية صغيرة — ملخّص نشاط الأسبوع في لوحة القيادة. */
type Day = { label: string; pct: number; isToday?: boolean }

export default function ChartBars({ days }: { days: Day[] }) {
  const entered = useEnter()
  return (
    <div className="mb-2.5 flex h-[88px] items-end gap-2">
      {days.map((day, i) => (
        <div key={i} className="flex h-full flex-1 flex-col items-center justify-end gap-1.5">
          <div
            className={`w-full max-w-[22px] rounded-t-[5px] rounded-b-[2px] transition-[height] duration-500 ease-out ${
              day.isToday ? 'bg-(--color-accent)' : 'bg-(--color-surface-2)'
            }`}
            style={{ height: entered ? `${day.pct}%` : 0 }}
          />
          <span className="text-[10px] text-(--color-text-dim)">{day.label}</span>
        </div>
      ))}
    </div>
  )
}
