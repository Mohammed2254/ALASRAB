/**
 * استيراد راصد — `schemas/paste.py` (FR-030..034 · FR-040). الاسم
 * («لصق») تاريخيّ لا وظيفيّ — الشاشة ترفع ملفًّا لا تعرض مربّع لصق نصّ
 * (`و-٥.md §٢` قرار #١٠). `value_overrides` بلا نوعٍ هنا عمدًا — بلا واجهة
 * بقرارٍ موروث (`و-١٨.md §١.٢`).
 */
import type { Count, Decimal } from '../brand'

// `PERCENT_CATEGORIES` في `services/paste.py` ثلاثةٌ ثابتة لا قاموسًا
// عامًّا — أدقّ من مخطّط `fields.Dict` الخلفيّ العامّ.
export type RasdPercentages = { hifz: string; thabat: string; muraja3a: string }

export type MatchStatus = 'matched' | 'ambiguous' | 'unmatched'

/** حالة الصفّ في الخطّة — أوسع من `MatchStatus`: مطابقةٌ بلا سربٍ نشط لا تُحتسب. */
export type RowPlanStatus = 'resolved' | 'unmatched' | 'ambiguous' | 'no_active_team'

/** الفئات الأربع التي يُنتجها ملفّ راصد — ثلاث نسبٍ زائد الحضور. */
export type RasdCategoryKey = 'hifz' | 'thabat' | 'muraja3a' | 'attendance'

/**
 * مصير فئةٍ واحدة. `no_ruleset`/`no_weight` حالتان معروضتان لا أعطال:
 * الأولى لا نسخة أوزان سارية، والثانية نشاطٌ بلا وزنٍ في النسخة السارية.
 */
export type RasdCategoryStatus =
  | 'created'
  | 'already_imported'
  | 'skipped_zero'
  | 'no_ruleset'
  | 'no_weight'

/** `hours` يغيب حين لا يكون للاحتساب معنى — فهو اختياريّ بالبنية لا بالسهو. */
export type RasdCategoryReport = { status: RasdCategoryStatus; hours?: Decimal }

export type PastePreviewRow = {
  name: string
  match_status: MatchStatus
  status: RowPlanStatus
  user_id: Count | null
  candidate_ids: Count[]
  percentages: RasdPercentages
  attendance: string
  tasmi3_days: string
  /** فارغة للصفوف غير المحسومة — لا خطّة لفئاتها أصلًا. */
  categories: Partial<Record<RasdCategoryKey, RasdCategoryReport>>
}

/** ما سيُكتب فعلًا، معدودًا قبل الكتابة — «لا استيراد بلا معاينة مقروءة». */
export type PastePreviewTotals = {
  rows: Count
  rows_resolved: Count
  rows_needing_attention: Count
  events_new: Count
  events_already_imported: Count
  events_skipped_zero: Count
  hours_total: Decimal
}

export type PastePreview = {
  batch_id: string
  duplicate_warning: boolean
  duplicate_imported_at: string | null
  /** تسميات صفوف التذييل المستبعَدة — الاستبعاد مُعلَن لا صامت. */
  excluded_labels: string[]
  weights_missing: boolean
  totals: PastePreviewTotals
  rows: PastePreviewRow[]
}

export type PasteRowResult = {
  name: string
  status: RowPlanStatus
  user_id: Count | null
}

export type PasteCommitResult = { batch_id: string; rows: PasteRowResult[]; events_created: Count }
