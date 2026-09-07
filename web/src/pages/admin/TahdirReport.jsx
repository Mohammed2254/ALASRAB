import Placard, { Row } from '../../components/Placard'
import { Async } from '../../components/States'
import { api } from '../../lib/api'
import { useAsync } from '../../state/useAsync'

/*
  تقرير تحضير القراءة الأسبوعي — و-١١ · FR-093.

  **كل رقم يأتي محسوبًا** من `GET /admin/tahdir/report` — النسبة والتعثّر
  والأيام المكتملة، بلا حساب هنا (AGENTS ٥). **يشمل من لم يُرسل شيئًا** —
  تقريرٌ يستبعد الغائبين يخفي بالضبط من يحتاج المشرف رؤيته.
*/

export default function TahdirReport({ onDone }) {
  const state = useAsync(() => api.tahdirReport(), [])

  return (
    <div className="taxi-in mx-auto w-full max-w-[520px] px-4 pt-6 pb-10">
      <header className="mb-5 flex items-baseline gap-3">
        <h1 className="font-display text-[26px] leading-none">تقرير تحضير القراءة</h1>
        <span className="centerline" />
        <button
          type="button"
          onClick={onDone}
          className="min-h-[44px] shrink-0 px-2 text-[13px] text-muted"
        >
          رجوع
        </button>
      </header>

      <Async state={state} loadingTitle="تقرير تحضير القراءة">
        {(report) => <Body report={report} />}
      </Async>
    </div>
  )
}

function Body({ report }) {
  if (report.students.length === 0) {
    return (
      <Placard title="الطلاب">
        <p className="py-2 text-[14px] text-muted">لا طلاب نشِطون بعد.</p>
      </Placard>
    )
  }

  return (
    <Placard title="هذا الأسبوع">
      {report.students.map((s) => (
        <div key={s.user_id} className="mb-2 border-b border-concrete/35 pb-2 last:border-0">
          <Row
            label={s.full_name}
            value={<bdi dir="ltr">{s.percent}%</bdi>}
            tone={s.struggling ? 'hold' : 'taxi'}
          />
          <p className="text-[12px] text-muted">
            <bdi dir="ltr">{s.days_completed}</bdi>/٤ أيام ·{' '}
            <bdi dir="ltr">{s.pages_total}</bdi> صفحة
          </p>
        </div>
      ))}
    </Placard>
  )
}
