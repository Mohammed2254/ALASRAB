import type { ReactNode } from 'react'

/** نبضة توهّج حول شارة — احتفال طيار الأسبوع. حركةٌ CSS محضة، لا GSAP. */
export default function CelebrateBadge({ children }: { children: ReactNode }) {
  return (
    <div className="mx-auto w-fit rounded-full [animation:celebrate-pulse_2.2s_ease-in-out_infinite]">{children}</div>
  )
}
