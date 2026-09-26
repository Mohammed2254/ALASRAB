/**
 * استيراد راصد — `schemas/paste.py` (FR-030..034 · FR-040). الاسم
 * («لصق») تاريخيّ لا وظيفيّ — الشاشة ترفع ملفًّا لا تعرض مربّع لصق نصّ
 * (`و-٥.md §٢` قرار #١٠). `value_overrides` بلا نوعٍ هنا عمدًا — بلا واجهة
 * بقرارٍ موروث (`و-١٨.md §١.٢`).
 */
import type { Count } from '../brand'

// `PERCENT_CATEGORIES` في `services/paste.py` ثلاثةٌ ثابتة لا قاموسًا
// عامًّا — أدقّ من مخطّط `fields.Dict` الخلفيّ العامّ.
export type RasdPercentages = { hifz: string; thabat: string; muraja3a: string }

export type MatchStatus = 'matched' | 'ambiguous' | 'unmatched'

export type PastePreviewRow = {
  name: string
  match_status: MatchStatus
  user_id: Count | null
  candidate_ids: Count[]
  percentages: RasdPercentages
  attendance: string
  tasmi3_days: string
}

export type PastePreview = {
  batch_id: string
  duplicate_warning: boolean
  duplicate_imported_at: string | null
  rows: PastePreviewRow[]
}

export type PasteRowResult = {
  name: string
  status: 'resolved' | 'unmatched' | 'ambiguous' | 'no_active_team'
  user_id: Count | null
}

export type PasteCommitResult = { batch_id: string; rows: PasteRowResult[]; events_created: Count }
