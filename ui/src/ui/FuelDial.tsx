import { fuelDialGeometry } from '../motion/geometry'
import { useEnter } from '../motion/useEnter'

/** عدّاد الوقود — قوس نصف دائريّ وعقرب، الهندسة في `motion/geometry.ts`. */
export default function FuelDial({ pct }: { pct: number }) {
  const entered = useEnter()
  const g = fuelDialGeometry(entered ? pct : 0)
  return (
    <div className="relative mx-auto mt-1 mb-0.5 h-[80px] w-[148px]">
      <svg viewBox="0 0 120 64" className="block h-full w-full overflow-visible" aria-hidden="true">
        <path d="M8 60 A52 52 0 0 1 112 60" fill="none" stroke="var(--color-surface-2)" strokeWidth={11} strokeLinecap="round" />
        <path
          d="M8 60 A52 52 0 0 1 112 60"
          fill="none"
          stroke="var(--color-accent)"
          strokeWidth={11}
          strokeLinecap="round"
          strokeDasharray={164}
          strokeDashoffset={g.arcOffset}
          className="transition-[stroke-dashoffset] duration-700 ease-out"
          style={{ filter: 'drop-shadow(0 0 5px var(--color-accent-glow))' }}
        />
      </svg>
      <div
        className="absolute bottom-2 left-1/2 h-[42px] w-0.5 -ml-px origin-bottom rounded-sm bg-(--color-text) transition-transform duration-700 ease-out after:absolute after:-bottom-1 after:left-1/2 after:h-[9px] after:w-[9px] after:-translate-x-1/2 after:rounded-full after:bg-(--color-text)"
        style={{ transform: `rotate(${g.needleDeg}deg)` }}
      />
    </div>
  )
}
