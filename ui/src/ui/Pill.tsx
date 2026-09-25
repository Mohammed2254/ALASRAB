import type { ReactNode } from 'react'

/** حبّة حالة ملوّنة. `size='md'` (الافتراضي) تحمل نقطة، `sm` لا تحملها. */
type Props = {
  tone: 'green' | 'red' | 'accent' | 'muted'
  size?: 'sm' | 'md'
  children: ReactNode
}

const TONE_CLASS: Record<Props['tone'], string> = {
  green: 'bg-(--color-green-tint) text-(--color-green)',
  red: 'bg-(--color-red-tint) text-(--color-red-text)',
  accent: 'bg-(--color-accent-tint) text-(--color-accent)',
  muted: 'bg-(--color-surface-2) text-(--color-text-dim)',
}

export default function Pill({ tone, size = 'md', children }: Props) {
  const sizing = size === 'md' ? 'px-3 py-1.5 text-[12px]' : 'px-2.5 py-1 text-[11px]'
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-semibold whitespace-nowrap ${sizing} ${TONE_CLASS[tone]}`}
    >
      {size === 'md' ? <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden="true" /> : null}
      {children}
    </span>
  )
}
