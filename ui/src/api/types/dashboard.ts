/**
 * لوحة القيادة — **نوعٌ مركَّب في الواجهة لا مخطَّطٌ خلفيّ.**
 *
 * لا مسار `/admin/dashboard` في `routes/admin.py`؛ اللوحة في النموذج المعتمد
 * تجميعٌ لخمسة مسارات قائمة. والتجميع يقع في `endpoints/admin.ts` لا في
 * الشاشة، فيوم يوجد مسارٌ مجمَّع حقيقيّ **تتغيّر تلك الدالّة وحدها والشاشة لا
 * تعلم**.
 *
 * وآمنٌ أمام `check-contract.mjs`: البوابة تمشي مخطّطات بايثون ⇒ TS وتحرس
 * اتّجاه «بايثون يضيف حقلًا»، ونوعٌ بلا مقابلٍ خلفيّ لا شيء يتعارض معه.
 */
import type { Count } from '../brand'
import type { AuditEntry } from './audit'
import type { ReportTotals, ReportWindow } from './report'

/** ما ينتظر إجراءً من المشرف — عددٌ لكلّ طابور، بلا تفصيل (التفصيل في شاشته). */
export type AdminPending = { readings: Count; tahdir: Count; notes: Count }

export type AdminDashboard = {
  /** نافذة التقرير — العنوان الفرعيّ يأتي من الخادم لا من ساعة المتصفّح. */
  window: ReportWindow
  totals: ReportTotals
  teams_count: Count
  pending: AdminPending
  activity: AuditEntry[]
}
