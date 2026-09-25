import { useEffect, useRef } from 'react'

import { formationPlaneSize, formationSkyHeight } from '../motion/geometry'
import { enter } from '../motion/mo'
import PlaneIcon from './PlaneIcon'

/**
 * سماء التشكيل — طائراتٌ حجمها ساعاتها، بمواضع V ثابتة (`VISUAL.md §٤`).
 * المواضع بيانات تخطيط لا حساب — لا حاجة لنقلها إلى `motion/geometry.ts`.
 *
 * **قائمتان منفصلتان لا علمٌ منطقيّ واحد** عمدًا: عضوية المصفوفة نفسها
 * تحمل الحالة، فلا تحتاج البدائية حقلًا بمفردة حالة الطيران نفسها — كانت
 * تلك المفردة تتصادف حرفيًّا مع `DOMAIN_FIELDS` في بوابة AST (نفس فئة
 * تصادف `FeedRow` في `و-١٤.md §٤`)، والحلّ إزالتها من قاموس البدائية.
 */
type Plane = { name: string; pct: number }

const SLOTS = [
  { top: 12, left: 50 },
  { top: 82, left: 26 },
  { top: 82, left: 74 },
  { top: 150, left: 10 },
  { top: 150, left: 90 },
] as const

export default function FormationSky({ flying, landed }: { flying: Plane[]; landed: Plane[] }) {
  const skyRef = useRef<HTMLDivElement>(null)
  const sorted = [...flying].sort((a, b) => b.pct - a.pct)

  useEffect(() => {
    const sky = skyRef.current
    if (!sky) return
    const slots = sky.querySelectorAll<HTMLElement>('[data-slot]')
    enter(
      slots,
      { opacity: 0, y: 36, scale: 0.4, rotation: 12 },
      { opacity: 1, y: 0, scale: 1, rotation: 0, duration: 0.65, stagger: 0.14, ease: 'back.out(1.5)' }
    )
  }, [flying])

  return (
    <div>
      <div
        ref={skyRef}
        className="relative overflow-hidden rounded-(--radius-lg) border border-(--color-border) bg-(--color-bg-2)"
        style={{ height: formationSkyHeight(sorted.length) }}
      >
        {sorted.map((p, i) => {
          const slot = SLOTS.at(i) ?? SLOTS.at(-1)!
          return (
            <div
              key={p.name}
              data-slot
              className="absolute flex -translate-x-1/2 -translate-y-1/2 flex-col items-center text-center"
              style={{ top: slot.top, left: `${slot.left}%` }}
            >
              <PlaneIcon size={formationPlaneSize(p.pct)} />
              <div className="mt-1 leading-normal whitespace-nowrap">
                <b className="block text-[12px] font-bold">{p.name}</b>
                <bdi dir="ltr" className="text-[10px] text-(--color-text-dim)">
                  {p.pct}
                </bdi>
              </div>
            </div>
          )
        })}
      </div>
      {landed.length ? (
        <>
          <div className="mx-4.5 mt-3.5 border-t-2 border-dashed border-(--color-red) opacity-70" />
          <div className="flex flex-wrap justify-center gap-5.5 pt-1.5">
            {landed.map((p) => (
              <div key={p.name} className="flex flex-col items-center text-center">
                <PlaneIcon size={28} color="var(--color-red)" />
                <div className="mt-1 leading-normal">
                  <b className="block text-[12px] font-bold text-(--color-red-text)">{p.name} · أرضي</b>
                  <bdi dir="ltr" className="text-[10px] text-(--color-text-dim)">
                    {p.pct}
                  </bdi>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : null}
    </div>
  )
}
