import { useLayoutEffect, useRef, useState } from 'react'

import HexIcon from './HexIcon'

/**
 * شريط التبويب السفليّ الثابت — شاشات الطيّار الخمس. نفس نمط قياس الموضع
 * في `SegmentedControl` (`useLayoutEffect` — لا قفزة من الصفر، ق-٢٢٩)،
 * بمؤشّرٍ مختلف الشكل (خطٌّ علويّ) لأنها بلاطات أيقونة+تسمية لا شرائح نصّ.
 */
export type Tab = { key: string; label: string; glyph: string }
type Props = { tabs: Tab[]; active: string; onSelect: (key: string) => void }

export default function BottomTabs({ tabs, active, onSelect }: Props) {
  const btnRefs = useRef<Record<string, HTMLButtonElement | null>>({})
  const [thumb, setThumb] = useState<{ left: number; width: number } | null>(null)

  useLayoutEffect(() => {
    const btn = btnRefs.current[active]
    if (!btn) return
    setThumb({ left: btn.offsetLeft, width: btn.offsetWidth })
  }, [active, tabs])

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-40 flex h-[74px] items-center justify-around border-t border-(--color-border) bg-(--color-bg-2)"
      aria-label="التنقّل الرئيسي"
    >
      {thumb ? (
        <span
          aria-hidden="true"
          className="absolute top-0 h-0.5 rounded-full bg-(--color-accent) transition-[transform,width] duration-300 ease-out"
          style={{ transform: `translateX(${thumb.left}px)`, width: thumb.width }}
        />
      ) : null}
      {tabs.map((tab) => {
        const isActive = tab.key === active
        return (
          <button
            key={tab.key}
            data-key={tab.key}
            ref={(el) => {
              btnRefs.current[tab.key] = el
            }}
            type="button"
            onClick={() => onSelect(tab.key)}
            className={`flex min-h-[44px] min-w-[44px] flex-col items-center gap-1 px-1.5 text-[10px] font-semibold ${
              isActive ? 'text-(--color-accent)' : 'text-(--color-text-dim)'
            }`}
          >
            <HexIcon size={22} glyph={tab.glyph} filled={isActive} />
            {tab.label}
          </button>
        )
      })}
    </nav>
  )
}
