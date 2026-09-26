/** الأوزان والعتبات — `schemas/rules_admin.py`. */
import type { Count, Decimal } from '../brand'

// ═══ الأوزان — FR-081 ═══

export type WeightRow = { activity_type: string; hours_per_unit: Decimal }
export type MultiplierRow = { grade: string; multiplier: Decimal }

export type CurrentWeightVersion = {
  id: Count
  effective_from: string
  note: string | null
  weights: WeightRow[]
  multipliers: MultiplierRow[]
}

export type WeightVersionRef = { id: Count; effective_from: string }
export type Weights = { current: CurrentWeightVersion | null; history: WeightVersionRef[] }

/** نموذج الإصدار الجديد كما يكتبه المشرف — الحقول العشرية نصوص إدخال هنا،
 * تصل `Decimal` بعد الحفظ فقط. `Number()` ممنوعة في الشاشة (`endpoints/admin.ts` يحوّل). */
export type WeightRowForm = { activity_type: string; hours_per_unit: string }
export type MultiplierRowForm = { grade: string; multiplier: string }
export type CreateWeightVersionForm = {
  effective_from: string
  note: string | null
  weights: WeightRowForm[]
  multipliers: MultiplierRowForm[]
}

// ═══ العتبات — FR-082 ═══

export type ThresholdRow = { key: string; name: string; tier: Count; at_hours: Decimal }
export type Thresholds = { thresholds: ThresholdRow[] }

/** `tier` نصّ إدخال هنا — نفس منطق نموذج الأوزان. */
export type ThresholdRowForm = { key: string; name: string; tier: string; at_hours: string }
export type SaveThresholdsForm = { thresholds: ThresholdRowForm[] }

export type RankShift = { user_id: Count; from_tier: Count; to_tier: Count }
export type ThresholdsPreview = { promoted: RankShift[]; demoted: RankShift[]; warning: string | null }
