import type { ReactNode } from 'react'

/** نصٌّ مكتوم لحالة لا محتوى فيها. */
export default function EmptyState({ children }: { children: ReactNode }) {
  return <p className="py-1.5 text-[13px] text-(--color-text-dim)">{children}</p>
}
