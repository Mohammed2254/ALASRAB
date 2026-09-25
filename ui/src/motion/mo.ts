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

/**
 * دخولٌ متدرّج (`stagger`) لعنصر أو مجموعة. تحت تقليل الحركة: القفزة مباشرةً
 * إلى `to` — لا حالة وسطى عالقة، ولا مدّة صفرية تترك GSAP يُنهي التوين على
 * إطار واحد بصمت (تلك مدّة قصيرة لا غياب حركة صريح).
 */
export function enter(targets: gsap.TweenTarget, from: gsap.TweenVars, to: gsap.TweenVars): void {
  if (reducedMotion()) {
    gsap.set(targets, to)
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
