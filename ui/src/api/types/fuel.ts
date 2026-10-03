/**
 * الوقود — الشقّ الإداريّ من `schemas/fuel.py` (FR-070 · FR-071). الشقّ
 * الطيّاريّ (محطة التزوّد، نفس الملفّ الخلفيّ) في `types/me.ts` —
 * مقسَّمان بحسب من يراهما (نفس منطق `types/adminQueue.ts` مقابل `me.ts`).
 */
import type { Count, Decimal } from '../brand'

export type CriterionRow = { key: string; name: string; weight_pct: Decimal }
export type CriterionOut = CriterionRow & { id: Count }
export type ActivityRow = { id: Count; key: string; name: string; litres_full: Decimal; criteria: CriterionOut[] }
export type ActivitiesList = { activities: ActivityRow[] }

/** نموذج الإنشاء كما يكتبه المشرف — `Decimal` كلّها نصوص إدخال هنا، تصل
 * `Decimal` بعد الحفظ فقط (نفس نمط نماذج و-١٧). */
export type CriterionRowForm = { key: string; name: string; weight_pct: string }
export type CreateActivityForm = { key: string; name: string; litres_full: string; criteria: CriterionRowForm[] }
export type CreatedActivity = { id: Count }

export type ScoreRowForm = { criterion_id: Count; score_pct: string }
export type AssessForm = { team_id: string; activity_id: string; occurred_on: string; scores: ScoreRowForm[] }
export type Assessed = { id: Count; total_pct: Decimal; litres: Decimal }

// ═══ أسبوع الوقود — و-٢٠ ═══

/**
 * حالة الأسبوع **حقلٌ معلَن لا استنتاج**: «مسوّدة» لا تُخمَّن من غياب
 * الدرجات، وإلّا التبست بـ«لم يُقيَّم بعد».
 */
export type FuelWeekState = 'unopened' | 'draft' | 'approved'

export type WeekCriterion = {
  id: Count
  name: string
  weight_pct: Decimal
  /** العدم = لم يُقيَّم بعد — لا صفر. */
  score_pct: Decimal | null
}

export type WeekTask = {
  activity_id: Count
  name: string
  litres_full: Decimal
  team_id: Count | null
  team_name: string | null
  assessed: boolean
  total_pct: Decimal
  litres: Decimal
  criteria: WeekCriterion[]
}

export type WeekTeamRef = { id: Count; name: string }

export type FuelWeek = {
  week_start: string
  state: FuelWeekState
  approved_at: string | null
  tasks: WeekTask[]
  teams: WeekTeamRef[]
  /**
   * نشاطٌ قائم ليس مهمّةً في هذا الأسبوع — «+ إضافة مهمة لهذا الأسبوع».
   * **يحسبه الخادم**: الفرقُ بين كلّ الأنشطة ومهامِّ الأسبوع قاعدةٌ لا عرض.
   * وفارغةٌ حين `unopened` لأن كل الأنشطة معروضةٌ مهامَّ افتراضية أصلًا.
   */
  available: WeekTeamRef[]
}
