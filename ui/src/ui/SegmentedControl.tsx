import { useLayoutEffect, useRef, useState } from 'react'

/**
 * شرائح بمؤشّر منزلق. الموضع يُقاس (`offsetLeft`/`offsetWidth`) في
 * `useLayoutEffect` — يعمل **قبل** الرسم الأوّل على الشاشة، فلا قفزة من
 * الصفر (ق-٢٢٩): العنصر يُدرَج في مكانه الصحيح مباشرةً، والانتقال يتحرّك
 * فقط حين يتغيّر الموضع لاحقًا — سلوك انتقال CSS الطبيعيّ على عنصر قائم،
 * لا على إدراجه الأوّل.
 */
type Option = { key: string; label: string }
type Props = { options: Option[]; value: string; onChange: (key: string) => void }

export default function SegmentedControl({ options, value, onChange }: Props) {
  const btnRefs = useRef<Record<string, HTMLButtonElement | null>>({})
  const [thumb, setThumb] = useState<{ left: number; width: number } | null>(null)

  useLayoutEffect(() => {
    const btn = btnRefs.current[value]
    if (!btn) return
    setThumb({ left: btn.offsetLeft, width: btn.offsetWidth })
  }, [value, options])

  return (
    <div className="relative mb-3.5 flex gap-2">
      {thumb ? (
        <span
          aria-hidden="true"
          className="absolute top-0 bottom-0 rounded-(--radius-sm) bg-(--color-accent-tint) transition-[transform,width] duration-300 ease-out"
          style={{ transform: `translateX(${thumb.left}px)`, width: thumb.width }}
        />
      ) : null}
      {options.map((opt) => (
        <button
          key={opt.key}
          data-key={opt.key}
          ref={(el) => {
            btnRefs.current[opt.key] = el
          }}
          type="button"
          onClick={() => onChange(opt.key)}
          className={`relative z-10 min-h-[40px] flex-1 rounded-(--radius-sm) border text-[13px] font-semibold ${
            opt.key === value
              ? 'border-(--color-accent) text-(--color-accent)'
              : 'border-(--color-border-strong) text-(--color-text-dim)'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}
