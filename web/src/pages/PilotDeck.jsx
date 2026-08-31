import Insignia from '../components/Insignia'
import Placard, { Row } from '../components/Placard'
import { Async } from '../components/States'
import { api } from '../lib/api'
import { useApp } from '../state/AppState'
import { useAsync } from '../state/useAsync'

/*
  بطاقة الطيار.

  **كل رقم هنا يأتي من `/api/me/deck` محسوبًا.** لا عتبة رتبة ولا قاعدة أربعة
  عشر يومًا ولا وزن صفحة في هذا الملفّ: الخادم يملك هذه القرارات، والواجهة
  تعرض نتيجتها (`AGENTS.md` ٥).

  ولو حُسبت هنا لتباعدت النسختان عند أوّل تعديل في العتبات، فرأى الطالب رتبة
  في بطاقته وأخرى في لوحة الصدارة — والثقة في الأرقام هي المنتج كلّه.
*/

/*
  تنسيق عرض بحت: التاريخ الميلادي بتوقيت المنظمة.

  **`nu-latn` مقصود:** الساعات والنسب تصل من الخادم نصوصًا لاتينية (`"611.25"`)،
  و`ar-SA` وحدها تعطي التاريخ أرقامًا عربية-هندية — فيجتمع نظامان في شاشة واحدة،
  وهو ما يمنعه `SCOPE.md` §١٠.٣. توحيدُهما على اللاتيني لأنه نظام البيانات
  الواصلة، والأرقام الجدولية في `Alexandria` مضبوطة له.
*/
const dateFormatter = new Intl.DateTimeFormat('ar-SA-u-ca-gregory-nu-latn', {
  day: 'numeric',
  month: 'long',
  timeZone: 'Asia/Riyadh',
})

const formatDay = (iso) => (iso ? dateFormatter.format(new Date(`${iso}T00:00:00Z`)) : null)

export default function PilotDeck({ onOpenReadings, onOpenQueue, onOpenReport }) {
  const { user, logout } = useApp()
  const state = useAsync(() => api.deck(), [])

  return (
    <div className="taxi-in mx-auto w-full max-w-[520px] px-4 pt-6 pb-10">
      <header className="mb-5 flex items-baseline gap-3">
        <h1 className="font-display text-[28px] leading-none">الأسراب</h1>
        <span className="centerline" />
        <button
          type="button"
          onClick={logout}
          className="min-h-[44px] shrink-0 px-2 text-[13px] text-muted"
        >
          خروج
        </button>
      </header>

      <Async state={state} loadingTitle="بطاقة الطيار">
        {(deck) => (
          <>
            <Card deck={deck} fullName={user.full_name} />
            <EventLog />
            <nav className="mt-4 flex flex-col gap-2">
              <button
                type="button"
                onClick={onOpenReadings}
                className="min-h-[48px] w-full border border-taxi text-[15px] text-taxi"
              >
                قراءاتي
              </button>
              {/* الدور من الخادم لا من الواجهة: إخفاء الزرّ راحةٌ لا حماية،
                  والصلاحية محروسة بـ@admin_required. */}
              {user.role === 'admin' && (
                <button
                  type="button"
                  onClick={onOpenQueue}
                  className="min-h-[48px] w-full border border-concrete/45 text-[15px] text-paint"
                >
                  طابور القراءات
                </button>
              )}
              {user.role === 'admin' && (
                <button
                  type="button"
                  onClick={onOpenReport}
                  className="min-h-[48px] w-full border border-concrete/45 text-[15px] text-paint"
                >
                  التقرير الدوري
                </button>
              )}
            </nav>
          </>
        )}
      </Async>
    </div>
  )
}

function Card({ deck, fullName }) {
  const { rank, hours, next_rank: next, flight, team } = deck

  return (
    <div className="flex flex-col gap-4">
      <Placard title="بطاقة الطيار">
        <div className="flex items-center gap-4">
          <Insignia tier={rank.tier} size={56} title={`شارة رتبة ${rank.name}`} />
          <div className="min-w-0">
            <h2 className="font-display text-[26px] leading-tight">{fullName}</h2>
            <p className="text-[14px] text-taxi">{rank.name}</p>
          </div>
        </div>

        <div className="mt-4 border-t border-concrete/35 pt-3">
          <Row label="ساعات الطيران" value={<bdi dir="ltr">{hours}</bdi>} tone="taxi" />
        </div>
      </Placard>

      <Progress next={next} />
      <Flight flight={flight} />
      <Team team={team} />
    </div>
  )
}

/*
  التقدّم داخل شريحة الرتبة — والنسبة تصل جاهزة من الخادم.

  في أعلى رتبة يأتي `next_rank: null`، فتُعرض **رسالة إتمام لا شريط ممتلئ**:
  شريطٌ عند ١٠٠٪ يوحي بأن هناك ما بعده لم يُبلغ (ق-٧).
*/
function Progress({ next }) {
  if (!next) {
    return (
      <Placard title="الرتبة">
        <p className="text-[15px] text-taxi">بلغتَ أعلى رتبة.</p>
        <p className="mt-1 text-[13px] text-muted">
          لا رتبة بعدها — ساعاتك تُسجَّل وتبقى في سجلّك.
        </p>
      </Placard>
    )
  }

  return (
    <Placard title="نحو الرتبة التالية" aside={next.name}>
      <div className="mb-2 flex items-baseline gap-3">
        <span className="shrink-0 text-[13px] text-muted">
          عند <bdi dir="ltr">{next.at_hours}</bdi> ساعة
        </span>
        <span className="centerline" style={{ opacity: 0.45 }} />
        <span className="shrink-0 text-[13px]">
          بقي <bdi dir="ltr">{next.remaining}</bdi>
        </span>
      </div>

      {/* الشريط يُملأ من اليمين: الاتجاه المنطقي يتكفّل به dir="rtl" في الجذر. */}
      <div
        className="h-2 w-full bg-taxiway"
        role="progressbar"
        aria-valuenow={next.progress_pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`التقدّم نحو ${next.name}`}
      >
        <div className="h-full bg-taxi" style={{ width: `${next.progress_pct}%` }} />
      </div>
      <p className="mt-1.5 text-[12px] text-muted">
        <bdi dir="ltr">{next.progress_pct}%</bdi> من هذه الشريحة
      </p>
    </Placard>
  )
}

/*
  حالة الطيران كما قرّرها الخادم.

  **قاعدة الأربعة عشر يومًا ليست هنا** — هي `orgs.grounded_after_days` في
  القاعدة، ويحسبها `services/readiness`. الواجهة تختار الشكل واللون والنصّ من
  قيمة منطقية وصلت جاهزة.

  والثلاثة معًا لا اللون وحده: من لا يميّز الأحمر يجب أن يقرأ حالته (ق-٨).
*/
/*
  علامة الحالة: SVG لا محرف إيموجي.

  الخطوط مستضافة محليًّا ولا خطّ إيموجي معها، فـ`⛔` يظهر مربّعًا فارغًا على أي
  نظام يفتقده — فتسقط قناة «الشكل» التي يوجبها `SCOPE.md` §١٠.٣ («بشكل ونصّ
  ولون معًا»). والشكلان من لغة علامات المطار: مربّع توقّف · مثلّث حركة.
*/
function FlightMark({ grounded }) {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true" className="shrink-0">
      {grounded ? (
        <rect x="1" y="1" width="10" height="10" fill="currentColor" />
      ) : (
        // يشير يسارًا: في واجهة RTL اتجاه الحركة والقراءة من اليمين إلى اليسار،
        // ومثلّثٌ يشير يمينًا يقرأ «رجوعًا» لا «تقدّمًا».
        <path d="M11 1 L1 6 L11 11 Z" fill="currentColor" />
      )}
    </svg>
  )
}

function Flight({ flight }) {
  const grounded = flight.grounded
  const day = formatDay(flight.last_activity_on)

  return (
    <Placard title="حالة الطيران">
      <Row
        label="الحالة"
        value={
          <span className="inline-flex items-center gap-2">
            <FlightMark grounded={grounded} />
            {grounded ? 'أرضي' : 'طائر'}
          </span>
        }
        tone={grounded ? 'hold' : 'default'}
      />
      <Row label="آخر نشاط" value={day ?? 'لا نشاط بعد'} tone={day ? 'default' : 'muted'} />
      <p className="mt-2 text-[13px] text-muted">
        {grounded
          ? 'سجّل قراءةً أو حفظًا جديدًا لتعود إلى الجوّ.'
          : day
            ? 'واصل، ونشاطك محسوب.'
            : 'أوّل نشاط لك يبدأ العدّ — ولا شيء ينقص قبله.'}
      </p>
    </Placard>
  )
}

/*
  السرب. `rank_in_org` قابل للعدم بعقدٍ معلَن (`API.md` §٤): ترتيب السرب FR-051
  يملكه `services/standings` في الوحدة ٩.

  **ولا يُحسب هنا** — نسخة ثانية من قاعدة الترتيب تفترق عن الأصل عند أوّل تعديل
  في فكّ التعادل، فيرى الطالب رقمين لسربه في شاشتين.
*/
function Team({ team }) {
  if (!team) {
    return (
      <Placard title="السرب">
        <p className="text-[14px] text-muted">لست في سرب حاليًّا. راجع المشرف.</p>
      </Placard>
    )
  }

  return (
    <Placard title="السرب">
      <Row label="الاسم" value={team.name} />
      <Row
        label="ترتيبه"
        value={team.rank_in_org ?? 'غير متاح بعد'}
        tone={team.rank_in_org == null ? 'muted' : 'default'}
      />
    </Placard>
  )
}


/*
  سجلّ الساعات — FR-012 · قصّة ط-٤.

  **يعرض ولا يحسب:** `delta` تصل نصًّا عشريًّا بإشارتها، والتصحيح يظهر سالبًا
  بسببه. «إخفاؤها هو ما يثير الشك لا إظهارها»: طالبٌ يرى رصيده نقص بلا سطر
  يفسّره يظنّ خللًا أو تلاعبًا.
*/
const KINDS = {
  quran: 'قرآن',
  reading: 'قراءة',
  attendance: 'حضور',
  daily_question: 'السؤال اليومي',
  correction: 'تصحيح',
  manual: 'إضافة يدوية',
}

function EventLog() {
  const state = useAsync(() => api.myEvents(10), [])

  return (
    <div className="mt-4">
      <Async state={state} loadingTitle="سجلّ ساعاتي">
        {(data) =>
          data.events.length ? (
            <Placard title="سجلّ ساعاتي" aside={`آخر ${data.events.length}`}>
              {data.events.map((e) => (
                <div key={e.id}>
                  <Row
                    label={KINDS[e.kind] ?? e.kind}
                    value={
                      <span>
                        <bdi dir="ltr">{e.delta}</bdi>{' '}
                        <span className="text-muted">{formatDay(e.occurred_on)}</span>
                      </span>
                    }
                    tone={e.kind === 'correction' ? 'hold' : 'default'}
                  />
                  {e.reason ? (
                    <p className="mb-1 text-[12px] text-hold">{e.reason}</p>
                  ) : null}
                </div>
              ))}
            </Placard>
          ) : (
            <Placard title="سجلّ ساعاتي">
              <p className="py-2 text-[14px] text-muted">
                لا أحداث بعد. أوّل إنجاز يبدأ سجلّك.
              </p>
            </Placard>
          )
        }
      </Async>
    </div>
  )
}
