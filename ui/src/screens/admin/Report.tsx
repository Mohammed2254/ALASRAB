import { useState } from 'react'

import { api, ApiError } from '../../api'
import { fmtDecimal } from '../../api/format'
import type { Grounded, ReportTeamRow } from '../../api/types/report'
import { useAsync } from '../../state/useAsync'
import { Async } from '../../ui/Async'
import type { Column } from '../../ui/DataTable'
import DataTable from '../../ui/DataTable'
import EmptyState from '../../ui/EmptyState'
import Placard from '../../ui/Placard'
import Prow from '../../ui/Prow'
import ErrorText from '../../ui/ErrorText'

/**
 * التقرير الدوري — `GET /admin/report` (FR-085). **كل رقم يصل محسوبًا**
 * (`AGENTS.md` ٥): مجموع النافذة ومعدّل السرب وأعلى المتحرّكين والساقطون،
 * بلا اشتقاق هنا. الساقطون بالاسم — شاشة إشراف لا صدارة طلاب (القرار ٥).
 */

const dayFormatter = new Intl.DateTimeFormat('ar-SA-u-ca-gregory-nu-latn', {
  day: 'numeric',
  month: 'long',
  timeZone: 'Asia/Riyadh',
})
const formatDay = (iso: string | null) => (iso ? dayFormatter.format(new Date(`${iso}T00:00:00Z`)) : null)

function GroundedRow({ pilot }: { pilot: Grounded }) {
  const [pin, setPin] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function reset() {
    setBusy(true)
    setError('')
    try {
      setPin((await api.admin.resetPin(pilot.user_id)).pin)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mb-2 border-b border-(--color-border) pb-2 last:border-none">
      <Prow label={pilot.full_name} value={formatDay(pilot.last_activity_on) ?? 'لا نشاط بعد'} tone="red" />
      {pin ? (
        <p className="mb-2 text-[13px] text-(--color-accent)">
          الرمز الجديد: <bdi dir="ltr">{pin}</bdi> — يُعرض مرّة واحدة، دوّنه الآن.
        </p>
      ) : (
        <button
          type="button"
          onClick={reset}
          disabled={busy}
          className="mb-2 min-h-[44px] w-full rounded-(--radius-sm) border border-(--color-border-strong) text-[13px] text-(--color-text-dim) disabled:opacity-40"
        >
          {busy ? 'جارٍ…' : 'إعادة تعيين الرمز'}
        </button>
      )}
      {error ? <ErrorText spacing="mb-2">{error}</ErrorText> : null}
    </div>
  )
}

/**
 * الأسراب وحدها جدول — بقيّة الألواح أزواجُ تسمية/قيمة، و`Prow` أصدقُ لها من
 * جدولٍ بعمودين.
 */
const TEAM_COLUMNS: Column<ReportTeamRow>[] = [
  { id: 'name', header: 'السرب', cell: (t) => t.name, primary: true },
  {
    id: 'avg',
    header: 'المعدّل',
    numeric: true,
    cell: (t) => <bdi dir="ltr" className="text-(--color-accent)">{fmtDecimal(t.avg_hours)}</bdi>,
  },
  {
    id: 'total',
    header: 'المجموع',
    numeric: true,
    cell: (t) => <bdi dir="ltr">{fmtDecimal(t.hours)}</bdi>,
  },
  {
    id: 'members',
    header: 'الأعضاء',
    numeric: true,
    cell: (t) => <bdi dir="ltr">{t.members}</bdi>,
  },
]

export default function Report() {
  const state = useAsync(() => api.admin.report(7), [])

  return (
    <div className="flex flex-col gap-3.5">
      <Async state={state} loadingTitle="التقرير">
        {(report) => (
          <div className="flex flex-col gap-3.5">
            <Placard title="الأسبوع" aside={`${formatDay(report.window.from)} — ${formatDay(report.window.to)}`}>
              <Prow label="مجموع الساعات" value={<bdi dir="ltr">{fmtDecimal(report.totals.hours)}</bdi>} tone="accent" />
              <Prow label="طيارون نشطون" value={<bdi dir="ltr">{report.totals.active_pilots}</bdi>} />
              <Prow
                label="طائرات أرضية"
                value={<bdi dir="ltr">{report.totals.grounded_pilots}</bdi>}
                tone={report.totals.grounded_pilots ? 'red' : undefined}
              />
            </Placard>

            <DataTable
              columns={TEAM_COLUMNS}
              rows={report.teams}
              rowKey={(t) => t.id}
              caption="الأسراب"
              empty="لا أسراب نشطة."
            />

            <Placard title="الأكثر تقدّمًا">
              {report.top_movers.length ? (
                report.top_movers.map((m) => (
                  <Prow key={m.user_id} label={m.full_name} value={<bdi dir="ltr">{fmtDecimal(m.hours)}</bdi>} tone="accent" />
                ))
              ) : (
                <EmptyState>لا نشاط في هذه النافذة.</EmptyState>
              )}
            </Placard>

            <Placard title="طائرات أرضية" aside="للمتابعة">
              {report.grounded.length ? (
                report.grounded.map((g) => <GroundedRow key={g.user_id} pilot={g} />)
              ) : (
                <EmptyState>كل الطيارين في الجوّ.</EmptyState>
              )}
            </Placard>
          </div>
        )}
      </Async>
    </div>
  )
}
