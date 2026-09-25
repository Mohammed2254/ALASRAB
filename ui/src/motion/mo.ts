/**
 * المكان الوحيد الذي يُفحص فيه `prefers-reduced-motion` (ADR-007) — بدائيةٌ
 * تستورد `enter`/`countUp` من هنا ولا تفحص الوسيلة بنفسها، فيبقى الاحترام
 * مضمونًا بمركزية الفحص لا بتكراره في كلّ ملفّ.
 *
 * واستيراد `gsap` **محصورٌ في هذا المجلّد** (`ui/src/motion/`) — يحرسه
 * `check-no-domain-logic.mjs`.
 */
import gsap from 'gsap'

export const reducedMotion = (): boolean =>
  typeof window !== 'undefined' &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

// مفاتيح توقيتٍ لا حالة — `gsap.set()` يقبلها نحويًّا لكنها تُبطئ تطبيقه:
// `stagger` تحديدًا **تؤجّل** الكتابة إلى دورة معالجة لاحقة حتى في `.set()`
// بلا مدّة، فيبقى العنصر بلا نمط مضبوط للحظة — بالضبط الحالة الوسطى العالقة
// التي صُمّم هذا الحارس لمنعها. مُثبَتٌ حيًّا: `gsap.set(el, {opacity:1,
// stagger:.16})` يترك `style.opacity` فارغة بعد العودة من النداء مباشرةً.
const TWEEN_ONLY_KEYS = ['duration', 'delay', 'ease', 'stagger', 'onComplete', 'onUpdate', 'onStart'] as const

function finalStyleOf(vars: gsap.TweenVars): gsap.TweenVars {
  const style = { ...vars }
  for (const key of TWEEN_ONLY_KEYS) delete style[key]
  return style
}

/**
 * دخولٌ متدرّج (`stagger`) لعنصر أو مجموعة. تحت تقليل الحركة: القفزة مباشرةً
 * إلى الحالة النهائية **بلا مفاتيح التوقيت** (`finalStyleOf`) — القفزة
 * ذاتها يجب أن تُطبَّق بلا انتظار دورة معالجة، وإلّا بقي العنصر بلا نمط
 * للحظة، وهي بالضبط الحالة الوسطى العالقة الممنوعة (ق-٢٣٠).
 */
export function enter(targets: gsap.TweenTarget, from: gsap.TweenVars, to: gsap.TweenVars): void {
  if (reducedMotion()) {
    gsap.set(targets, finalStyleOf(to))
    return
  }
  gsap.fromTo(targets, from, to)
}

/**
 * عدّاد أرقام يتصاعد. تحت تقليل الحركة: النصّ النهائي فورًا بلا تصاعد.
 * `decimals` لأن ساعات الطيران عشريّة (`611.25`) بينما نسب الوقود صحيحة.
 */
export function countUp(
  el: HTMLElement | null,
  target: number,
  opts: { duration?: number; decimals?: 0 | 2; suffix?: string } = {}
): void {
  if (!el) return
  const { duration = 1, decimals = 0, suffix = '' } = opts
  const write = (v: number) => {
    el.textContent = v.toFixed(decimals) + suffix
  }
  if (reducedMotion()) {
    write(target)
    return
  }
  const obj = { v: 0 }
  gsap.to(obj, { v: target, duration, ease: 'power2.out', onUpdate: () => write(obj.v) })
}
