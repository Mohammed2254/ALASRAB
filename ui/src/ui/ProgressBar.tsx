import { progressScaleX } from '../motion/geometry'
import { useEnter } from '../motion/useEnter'

/**
 * مسارٌ خطّي + تعبئة — البدائية الواحدة وراء ثلاثة أشكال في النموذج
 * (`bar-fill`/`gauge-fill`/`prog-fill`) كانت نفس الآلية بثلاث نسخ (`و-١٤.md §١.٣`).
 */
type Props = { pct: number; height?: number; glow?: boolean }

export default function ProgressBar({ pct, height = 6, glow = false }: Props) {
  const entered = useEnter()
  const scale = entered ? progressScaleX(pct) : 0
  return (
    <div
      className="overflow-hidden rounded-full bg-(--color-surface-2)"
      style={{ height }}
      role="progressbar"
      aria-valuenow={pct}
    >
      <div
        className="h-full origin-right rounded-full bg-(--color-accent) transition-transform duration-700 ease-out"
        style={{ transform: `scaleX(${scale})`, boxShadow: glow ? '0 0 8px var(--color-accent-glow)' : undefined }}
      />
    </div>
  )
}
