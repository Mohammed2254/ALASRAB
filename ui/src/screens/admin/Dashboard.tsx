import { api } from '../../api'
import type { AuditEntry } from '../../api/types/audit'
import { go } from '../../nav/history'
import { useAsync } from '../../state/useAsync'
import { Async } from '../../ui/Async'
import FeedRow from '../../ui/FeedRow'
import type { FeedIcon } from '../../ui/feedIcons'
import Placard from '../../ui/Placard'
import StatCard from '../../ui/StatCard'
import TaskRow from '../../ui/TaskRow'

/**
 * لوحة القيادة — أوّل ما يرى المشرف.
 *
 * **كانت غائبةً كليًّا** حتى و-٢٠: أُسقطت في و-١٧ بحجّة «لا مسار خلفيّ يقابلها»،
 * وهي في النموذج المعتمد **تجميعٌ لخمسة مسارات قائمة** لا نقطةٌ جديدة. والتجميع
 * في `api.admin.dashboard()` لا هنا، فالشاشة حالةُ تحميلٍ واحدة وحالةُ خطأ
 * واحدة وإعادةُ تحميلٍ واحدة تُنعش الخمسة معًا.
 *
 * وكل رقمٍ يصل محسوبًا — لا حساب هنا (`AGENTS.md` ٥).
 */

/**
 * لهجة صفّ النشاط.
 *
 * **كلّها `accent` عمدًا، وهذا انحرافٌ مقصود عن نقاط النموذج الملوّنة.**
 * `VISUAL.md §٢` يقنّن الأحمر لفئتين حصرًا (نتيجة سلبية في منطق المنتج · خطأ
 * تقنيّ) والأخضر لـ«نشط» حصرًا — و`AuditEntry.kind` القائمة ليس فيها حدثُ
 * تأريضٍ ولا رفضِ قراءة، أي لا واحدة منها تستحقّ لونًا مأذونًا. فالنقاط
 * الملوّنة في النموذج بياناتٌ تجريبية لأحداثٍ لا نُصدرها بعد؛ ويوم تُضاف
 * أنواعُها يصير الأحمر مستحقًّا بالفئة أ لا بالذوق.
 */
const ACTIVITY_ICON: Record<string, FeedIcon> = {
  pin_reset: 'key',
  weights_version: 'trend',
  thresholds_update: 'trend',
  team_created: 'plus',
  team_archived: 'cross',
  membership_transferred: 'arrow',
  quran_correction: 'check',
  rasd_import: 'download',
}

const ReviewButton = ({ onClick }: { onClick: () => void }) => (
  <button
    type="button"
    onClick={onClick}
    className="min-h-[44px] rounded-(--radius-sm) border border-(--color-accent) px-3.5 text-[12px] font-semibold text-(--color-accent)"
  >
    مراجعة
  </button>
)

function Activity({ entries }: { entries: AuditEntry[] }) {
  if (entries.length === 0) {
    return <p className="py-2 text-[13px] text-(--color-text-dim)">لا نشاط مسجَّل بعد.</p>
  }
  return (
    <>
      {entries.map((e) => (
        <FeedRow
          key={e.id}
          tone="accent"
          icon={ACTIVITY_ICON[e.kind] ?? 'line'}
          text={e.summary}
          time={e.actor_name}
        />
      ))}
    </>
  )
}

export default function Dashboard() {
  const state = useAsync(() => api.admin.dashboard(), [])

  return (
    <Async state={state} loadingTitle="لوحة القيادة">
      {(d) => {
        const quiet =
          d.pending.readings === 0 && d.pending.tahdir === 0 && d.pending.notes === 0
        return (
          <div className="flex flex-col gap-3.5">
            <p className="text-[12px] text-(--color-text-dim)">
              الأسبوع — من <bdi dir="ltr">{d.window.from}</bdi> إلى{' '}
              <bdi dir="ltr">{d.window.to}</bdi>
            </p>

            <div className="grid grid-cols-2 gap-2.5 desk:grid-cols-4">
              <StatCard value={d.totals.active_pilots} label="طيّارون نشطون" />
              <StatCard value={d.teams_count} label="الأسراب" />
              <StatCard value={d.totals.grounded_pilots} label="طائرات أرضيّة" tone="danger" />
              <StatCard
                value={d.totals.hours}
                label="ساعات هذا الأسبوع"
                tone="accent"
                decimals={2}
              />
            </div>

            <Placard title="بحاجة إلى إجراء منك">
              {quiet ? (
                <p className="py-2 text-[13px] text-(--color-text-dim)">
                  لا شيء معلَّق — كل الطوابير فارغة.
                </p>
              ) : (
                <>
                  {d.pending.readings ? (
                    <TaskRow
                      label="قراءات تنتظر الاعتماد"
                      count={<bdi dir="ltr">{d.pending.readings}</bdi>}
                      action={<ReviewButton onClick={() => go('adminQueue')} />}
                    />
                  ) : null}
                  {d.pending.tahdir ? (
                    <TaskRow
                      label="تحضيرات تنتظر الاعتماد"
                      count={<bdi dir="ltr">{d.pending.tahdir}</bdi>}
                      action={<ReviewButton onClick={() => go('adminTahdirQueue')} />}
                    />
                  ) : null}
                  {d.pending.notes ? (
                    <TaskRow
                      label="ملاحظات لم تُقرأ"
                      count={<bdi dir="ltr">{d.pending.notes}</bdi>}
                      action={<ReviewButton onClick={() => go('adminNotes')} />}
                    />
                  ) : null}
                </>
              )}
            </Placard>

            <Placard title="النشاط الأخير">
              <Activity entries={d.activity} />
            </Placard>
          </div>
        )
      }}
    </Async>
  )
}
