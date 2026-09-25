import type { ReactNode } from 'react'

/** صفّ حدث بنقطة أيقونة ملوّنة — الصندوق الأسود والنشاط الأخير. */
type Props = { tone: 'green' | 'red' | 'accent'; icon: string; text: ReactNode; time: ReactNode }

const DOT_CLASS: Record<Props['tone'], string> = {
  green: 'bg-(--color-green-tint) text-(--color-green)',
  red: 'bg-(--color-red-tint) text-(--color-red-text)',
  accent: 'bg-(--color-accent-tint) text-(--color-accent)',
}

export default function FeedRow({ tone, icon, text, time }: Props) {
  return (
    <div className="flex items-start gap-3 border-b border-(--color-border) py-2.5 last:border-none">
      <div className={`flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-[9px] ${DOT_CLASS[tone]}`}>
        <svg width={16} height={16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" aria-hidden="true">
          <path d={icon} />
        </svg>
      </div>
      <div>
        <div className="text-[13px]">{text}</div>
        <div className="mt-0.5 text-[11px] text-(--color-text-dim)">{time}</div>
      </div>
    </div>
  )
}
