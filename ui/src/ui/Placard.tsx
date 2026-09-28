import type { ReactNode } from 'react'

/**
 * اللوح — الحاوية الوحيدة (`VISUAL.md §٥`). لا لوح داخل لوح.
 */
type Props = {
  /** `ReactNode` لا `string`: عنوان بطاقة الصفّ في `DataTable` خليّةٌ مُنسَّقة. */
  title: ReactNode
  aside?: ReactNode
  children: ReactNode
}

export default function Placard({ title, aside, children }: Props) {
  return (
    <section className="mb-3.5 rounded-(--radius-lg) border border-(--color-border) bg-(--color-surface) p-5">
      <div className="mb-3.5 flex items-baseline justify-between gap-2.5">
        <h3 className="text-[14px] font-bold">{title}</h3>
        {aside ? <span className="text-[11px] whitespace-nowrap text-(--color-text-dim)">{aside}</span> : null}
      </div>
      {children}
    </section>
  )
}
