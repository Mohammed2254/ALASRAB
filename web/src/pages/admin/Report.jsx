import { useState } from 'react'

import Placard, { Row } from '../../components/Placard'
import { Async } from '../../components/States'
import { api } from '../../lib/api'
import { useAsync } from '../../state/useAsync'

/*
  التقرير الدوري — FR-085 · ف-٧: «صفحة داخل المنصة لا ملفًّا مُصدَّرًا».

  **كل رقم يأتي محسوبًا** من `GET /admin/report`: مجموع النافذة، ومعدّل السرب،
  وأعلى المتحرّكين، والساقطون. ولا يُشتقّ شيء هنا — والمعدّل تحديدًا لو حُسب في
  الواجهة لافترق عن صدارة الأسراب عند أوّل تعديل.

  والساقطون **بالاسم** لأنها شاشة إشراف: القرار ٥ يمنع عرضهم للطلاب، ومن يلاحق
  الطالب يحتاج أن يعرف من يلاحق.
*/

const dayFormatter = new Intl.DateTimeFormat('ar-SA-u-ca-gregory-nu-latn', {
  day: 'numeric',
  month: 'long',
  timeZone: 'Asia/Riyadh',
})

const formatDay = (iso) => (iso ? dayFormatter.format(new Date(`${iso}T00:00:00Z`)) : null)

export default function Report({ onDone }) {
  const state = useAsync(() => api.report(7), [])

  return (
    <div className="taxi-in mx-auto w-full max-w-[520px] px-4 pt-6 pb-10">
      <header className="mb-5 flex items-baseline gap-3">
        <h1 className="font-display text-[26px] leading-none">التقرير الدوري</h1>
        <span className="centerline" />
        <button
          type="button"
          onClick={onDone}
          className="min-h-[44px] shrink-0 px-2 text-[13px] text-muted"
        >
          رجوع
        </button>
      </header>

      <Async state={state} loadingTitle="التقرير">
        {(report) => <Body report={report} />}
      </Async>
    </div>
  )
}

function Body({ report }) {
  const { window: win, totals, teams, top_movers: movers, grounded } = report

  return (
    <div className="flex flex-col gap-4">
      <Placard title="الأسبوع" aside={`${formatDay(win.from)} — ${formatDay(win.to)}`}>
        <Row label="مجموع الساعات" value={<bdi dir="ltr">{totals.hours}</bdi>} tone="taxi" />
        <Row label="طيارون نشطون" value={<bdi dir="ltr">{totals.active_pilots}</bdi>} />
        <Row
          label="طائرات أرضية"
          value={<bdi dir="ltr">{totals.grounded_pilots}</bdi>}
          tone={totals.grounded_pilots ? 'hold' : 'muted'}
        />
      </Placard>

      <Placard title="الأسراب" aside="بالمعدّل">
        {teams.map((t) => (
          <Row
            key={t.id}
            label={t.name}
            value={
              <span>
                <bdi dir="ltr">{t.avg_hours}</bdi>{' '}
                <span className="text-muted">
                  (<bdi dir="ltr">{t.members}</bdi>)
                </span>
              </span>
            }
          />
        ))}
      </Placard>

      <Placard title="الأكثر تقدّمًا">
        {movers.length ? (
          movers.map((m) => (
            <Row
              key={m.user_id}
              label={m.full_name}
              value={<bdi dir="ltr">{m.hours}</bdi>}
              tone="taxi"
            />
          ))
        ) : (
          <p className="py-2 text-[14px] text-muted">لا نشاط في هذه النافذة.</p>
        )}
      </Placard>

      <Placard title="طائرات أرضية" aside="للمتابعة">
        {grounded.length ? (
          grounded.map((g) => <GroundedRow key={g.user_id} pilot={g} />)
        ) : (
          <p className="py-2 text-[14px] text-muted">كل الطيارين في الجوّ.</p>
        )}
      </Placard>
    </div>
  )
}


/*
  صفّ طيار أرضيّ، ومعه إعادة تعيين الرمز (FR-004).

  **موضعها هنا لا في شاشة مستقلّة:** المشرف يحتاجها حين يلاحق طالبًا لا يظهر —
  وأشيع سبب لغيابه أنه لا يستطيع الدخول. وضعُها في مكان الملاحقة يوفّر شاشةً
  كاملة ونقرتين.

  **والرمز يُعرض مرّة واحدة** ولا سبيل لاسترجاعه — فالنصّ يقولها صراحةً.
*/
function GroundedRow({ pilot }) {
  const [pin, setPin] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function reset() {
    setBusy(true)
    setError('')
    try {
      setPin((await api.resetPin(pilot.user_id)).pin)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <Row
        label={pilot.full_name}
        value={formatDay(pilot.last_activity_on) ?? 'لا نشاط بعد'}
        tone="hold"
      />
      {pin ? (
        <p className="mb-2 text-[13px] text-taxi">
          الرمز الجديد: <bdi dir="ltr">{pin}</bdi> — يُعرض مرّة واحدة، دوّنه الآن.
        </p>
      ) : (
        <button
          type="button"
          onClick={reset}
          disabled={busy}
          className="mb-2 min-h-[44px] w-full border border-concrete/45 text-[13px] text-muted disabled:opacity-40"
        >
          {busy ? 'جارٍ…' : 'إعادة تعيين الرمز'}
        </button>
      )}
      {error ? (
        <p role="alert" className="mb-2 text-[13px] text-hold">
          {error}
        </p>
      ) : null}
    </div>
  )
}
