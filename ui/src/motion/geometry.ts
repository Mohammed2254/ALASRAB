/**
 * كل الحساب الهندسيّ للحركة — المكان الوحيد المسموح فيه بعمليات حسابية على
 * نسبة (ADR-007). البدائيات تستورد هذه الدوالّ ولا تحسب بنفسها؛ العمليات
 * الحسابية والمقارنات ممنوعة في `src/ui/**` بفحص AST، ومسموحة هنا حصرًا —
 * ويحرس الاستثناءَ فحصٌ ثانٍ: `motion/geometry` لا تُستورَد خارج `motion/`.
 *
 * هندسةُ رسمٍ ليست قاعدة عمل: لا تقرّر رتبةً ولا عتبةً ولا وزنًا، والنِّسَب
 * التي تستقبلها (`pct`) تصل محسوبة من الخادم بالفعل.
 */

const clampPct = (pct: number): number => Math.max(0, Math.min(100, pct))

/** مسار خطّي: نسبة ← معامل تحجيم أفقي (٠..١) لـ`transform: scaleX()`. */
export function progressScaleX(pct: number): number {
  return clampPct(pct) / 100
}

/**
 * عدّاد الوقود — قوس نصف دائريّ طوله ١٦٤ وحدة (`stroke-dasharray`)، وعقربٌ
 * يدور من ‎-90°‏ (صفر) إلى ‎+90°‏ (١٠٠٪) — مسحٌ ١٨٠°. القيم منقولة حرفيًّا من
 * النموذج المعتمد.
 */
const FUEL_ARC_LENGTH = 164
const FUEL_NEEDLE_START_DEG = -90
const FUEL_NEEDLE_SWEEP_DEG = 180

export function fuelDialGeometry(pct: number): { arcOffset: number; needleDeg: number } {
  const p = clampPct(pct)
  return {
    arcOffset: FUEL_ARC_LENGTH * (1 - p / 100),
    needleDeg: FUEL_NEEDLE_START_DEG + (p / 100) * FUEL_NEEDLE_SWEEP_DEG,
  }
}

/**
 * حجم طائرة التشكيل: من ٢٦px (صفر) إلى ٥٢px (١٠٠٪) بتدرّج خطّي — «حجم
 * طائرتك = ساعاتك» (`VISUAL.md §٤`).
 */
const FORMATION_MIN_SIZE = 26
const FORMATION_MAX_GROWTH = 26

export function formationPlaneSize(pct: number): number {
  return FORMATION_MIN_SIZE + (clampPct(pct) / 100) * FORMATION_MAX_GROWTH
}

/**
 * اتّجاه تغيّر ترتيب — ▲/▼/– (`ChgBadge`). المقارنات (`<`/`>`) والقيمة
 * المطلَقة (`Math.abs`) ممنوعتان في طبقة العرض، فالقرار والمقدار يُحسَبان
 * هنا معًا.
 */
export function chgDirection(chg: number): { direction: 'up' | 'down' | 'same'; magnitude: number } {
  if (chg === 0) return { direction: 'same', magnitude: 0 }
  const direction = chg > 0 ? 'up' : 'down'
  const magnitude = direction === 'up' ? chg : -chg
  return { direction, magnitude }
}

/**
 * ارتفاع حاوية سماء التشكيل — يكبر مع عدد الطائرات المحلِّقة كي لا تتزاحم
 * فتحجب شارة بعضها بعضًا. عتباتٌ منقولة حرفيًّا من النموذج المعتمد.
 */
export function formationSkyHeight(flyingCount: number): number {
  if (flyingCount > 3) return 210
  if (flyingCount > 1) return 172
  return 110
}
