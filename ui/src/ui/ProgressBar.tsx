import { progressScaleX } from '../motion/geometry'
import { useEnter } from '../motion/useEnter'
import PlaneIcon from './PlaneIcon'

/**
 * مسارٌ خطّي + تعبئة — البدائية الواحدة وراء ثلاثة أشكال في النموذج
 * (`bar-fill`/`gauge-fill`/`prog-fill`) كانت نفس الآلية بثلاث نسخ (`و-١٤.md §١.٣`).
 *
 * **و`rider` طائرةٌ تركب حافّة التعبئة** — لحظةٌ توقيعية من النموذج (و-٢٠).
 * وهي **شقيقةُ الحشو لا ابنته**: ابنُ عنصرٍ عليه `scaleX` يُسحق بنفس
 * النسبة فيصير شكلًا مشوَّهًا. وموضعُها بخاصّية CSS مخصّصة و`calc()`،
 * فالضرب يقع في CSS لا في TS — ولا عقدة حسابٍ تدخل فحص AST.
 *
 * **والمسار RTL:** التعبئة تنمو من اليمين (`origin-right`)، فحافّتُها
 * المتقدّمة على اليسار — أي `right: نسبة%`. وإشارةُ المحور أشهر عطلٍ في هذا
 * الصنف، فقِيست في متصفّحٍ حقيقيّ لا استُنتجت.
 */
type Props = { pct: number; height?: number; glow?: boolean; rider?: true | undefined }

export default function ProgressBar({ pct, height = 6, glow = false, rider }: Props) {
  const entered = useEnter()
  const scale = entered ? progressScaleX(pct) : 0

  const track = (
    <div
      className="h-full overflow-hidden rounded-full bg-(--color-surface-2)"
      role="progressbar"
      aria-valuenow={pct}
    >
      <div
        className="h-full origin-right rounded-full bg-(--color-accent) transition-transform duration-700 ease-out"
        style={{
          transform: `scaleX(${scale})`,
          boxShadow: glow ? '0 0 8px var(--color-accent-glow)' : undefined,
        }}
      />
    </div>
  )

  if (!rider) return <div style={{ height }}>{track}</div>

  return (
    // `--p` نسبةٌ بلا وحدة تقرأها `calc` — والحاوية بلا `overflow-hidden`
    // وإلّا قُصّت الطائرة عند الحافّة.
    <div
      className="relative"
      style={{ height, ['--p' as string]: scale }}
    >
      {track}
      <span
        aria-hidden="true"
        className="absolute top-1/2 -translate-y-1/2 translate-x-1/2 text-(--color-accent) transition-[right] duration-700 ease-out"
        style={{ right: 'calc(var(--p) * 100%)' }}
      >
        <PlaneIcon size={16} />
      </span>
    </div>
  )
}
