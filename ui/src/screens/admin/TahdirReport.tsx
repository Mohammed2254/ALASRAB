import { useState } from 'react'

import { api } from '../../api'
import type { OrgTahdirRow, TahdirTier } from '../../api/types/adminQueue'
import { useAsync } from '../../state/useAsync'
import { Async } from '../../ui/Async'
import Button from '../../ui/Button'
import type { Column } from '../../ui/DataTable'
import DataTable from '../../ui/DataTable'
import Field, { fieldClass } from '../../ui/Field'
import Pill from '../../ui/Pill'
import Placard from '../../ui/Placard'
import StatCard from '../../ui/StatCard'

/**
 * تقرير تحضير القراءة — **بفترة محدَّدة** كما في النموذج المعتمد.
 *
 * ودرجةُ الانتظام (`tier`) تصل **محسوبة من الخادم** بعتبتَي ٠٫٩ و٠٫٥: هي
 * قاعدة عمل لا عرض، والشاشة تُلوّن وتُسمّي فقط (`AGENTS.md` ٥).
 *
 * **والأخضر هنا مأذون** بالمعنى المقنَّن في `VISUAL.md §٢`: «ممتاز» و«منتظمون
 * بالكامل» حالةُ **نشاط** لا زينة. والأحمر مأذون بالفئة أ — «يحتاج متابعة»
 * نتيجةٌ سلبية داخل منطق المنتج.
 */
const TIER: Record<TahdirTier, { label: string; tone: 'green' | 'accent' | 'red' }> = {
  good: { label: 'ممتاز', tone: 'green' },
  fair: { label: 'منتظم', tone: 'accent' },
  low: { label: 'يحتاج متابعة', tone: 'red' },
}


const COLUMNS: Column<OrgTahdirRow>[] = [
  { id: 'name', header: 'الطالب', cell: (s) => s.full_name, primary: true },
  { id: 'team', header: 'السرب', cell: (s) => s.team_name },
  {
    id: 'days',
    header: 'أيام نشطة',
    numeric: true,
    cell: (s) => (
      <bdi dir="ltr">
        {s.days_completed}/{s.days_total}
      </bdi>
    ),
  },
  {
    id: 'pages',
    header: 'الصفحات',
    numeric: true,
    cell: (s) => <bdi dir="ltr">{s.pages_total}</bdi>,
  },
  {
    id: 'tier',
    header: 'الحالة',
    cell: (s) => (
      <Pill tone={TIER[s.tier].tone} size="sm">
        {TIER[s.tier].label}
      </Pill>
    ),
  },
]

export default function TahdirReport() {
  // نصّان خامّان حتى الإصدار — الخادم يرفض فترةً بطرفٍ واحد أو مقلوبة،
  // فلا فحص نطاقٍ هنا (`AGENTS.md` ٥).
  const [draft, setDraft] = useState({ from: '', to: '' })
  const [applied, setApplied] = useState<{ from: string; to: string } | null>(null)
  const state = useAsync(
    () => api.admin.tahdirReport(applied?.from, applied?.to),
    [applied?.from, applied?.to]
  )

  return (
    <div className="flex flex-col gap-3.5">
      <Placard title="إصدار تقرير بفترة محدَّدة">
        <div className="grid grid-cols-2 gap-x-3">
          <Field label="من تاريخ" htmlFor="tr_from">
            <input
              id="tr_from"
              type="date"
              value={draft.from}
              onChange={(e) => setDraft((d) => ({ ...d, from: e.target.value }))}
              className={fieldClass}
            />
          </Field>
          <Field label="إلى تاريخ" htmlFor="tr_to">
            <input
              id="tr_to"
              type="date"
              value={draft.to}
              onChange={(e) => setDraft((d) => ({ ...d, to: e.target.value }))}
              className={fieldClass}
            />
          </Field>
        </div>
        <Button
          disabled={!draft.from || !draft.to}
          onClick={() => setApplied({ from: draft.from, to: draft.to })}
          className="w-full"
        >
          إصدار تقرير القراءة
        </Button>
        {applied ? (
          <button
            type="button"
            onClick={() => setApplied(null)}
            className="mt-2 min-h-[44px] w-full rounded-(--radius-sm) border border-(--color-border-strong) text-[13px] text-(--color-text-dim)"
          >
            العودة إلى أسبوع اليوم
          </button>
        ) : null}
      </Placard>

      <Async state={state} loadingTitle="تقرير تحضير القراءة">
        {(report) => (
          <>
            <p className="text-[12px] text-(--color-text-dim)">
              من <bdi dir="ltr">{report.from_day}</bdi> إلى <bdi dir="ltr">{report.to_day}</bdi> —{' '}
              <bdi dir="ltr">{report.days_total}</bdi> يوم تحضير
            </p>

            <div className="grid grid-cols-3 gap-2.5">
              <StatCard value={report.totals.pages} label="مجموع صفحات التحضير" />
              <StatCard value={report.totals.participants} label="طلّاب مشاركون" />
              <StatCard
                value={report.totals.fully_regular}
                label="منتظمون بالكامل"
                tone="accent"
              />
            </div>

            <DataTable
              columns={COLUMNS}
              rows={report.students}
              rowKey={(s) => s.user_id}
              caption="تفصيل كل طالب"
              empty="لا طلاب نشِطون في هذه الفترة."
            />
          </>
        )}
      </Async>
    </div>
  )
}
