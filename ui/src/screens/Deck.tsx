import { useEffect, useRef } from 'react'

import { api } from '../api'
import type { Deck as DeckData } from '../api/types/me'
import { fmtDecimal } from '../api/format'
import { countUp } from '../motion/mo'
import { useAsync } from '../state/useAsync'
import { Async } from '../ui/Async'
import FeedRow from '../ui/FeedRow'
import HexIcon from '../ui/HexIcon'
import Placard from '../ui/Placard'
import ProgressBar from '../ui/ProgressBar'
import Prow from '../ui/Prow'

/**
 * بطاقة الطيّار — `GET /me/deck` + `GET /me/events`. **كل رقم يصل محسوبًا**
 * (`AGENTS.md` ٥): لا عتبة رتبة ولا مهلة أرضيّ هنا، الخادم يملك هذين القرارين.
 */

const dateFormatter = new Intl.DateTimeFormat('ar-SA-u-ca-gregory-nu-latn', {
  day: 'numeric',
  month: 'long',
  timeZone: 'Asia/Riyadh',
})
const formatDay = (iso: string | null) => (iso ? dateFormatter.format(new Date(`${iso}T00:00:00Z`)) : null)

const KINDS: Record<string, string> = {
  quran: 'قرآن',
  reading: 'قراءة',
  attendance: 'حضور',
  daily_question: 'السؤال اليومي',
  correction: 'تصحيح',
  manual: 'إضافة يدوية',
}
// مقاس ٢٤×٢٤ — نفس منظومة `viewBox` في `FeedRow`، لا ٦٤×٦٤ الخاصّة بـ`HexIcon`.
// الخطأ السابق (إحداثيات حتّى ٤٢ داخل صندوق ٢٤) كان يرسم علامةً أكبر من
// الصندوق بمرّتين فتخرج عن الرؤية — مُكتشَفٌ بمعاينة حيّة لا افتراضًا.
const CHECK = 'M5 12l4 4L19 6'
const WARN = 'M6 6l12 12M18 6L6 18'

function Hero({ deck }: { deck: DeckData }) {
  const hoursRef = useRef<HTMLElement>(null)

  useEffect(() => {
    countUp(hoursRef.current, deck.hours, { decimals: 2 })
  }, [deck.hours])

  return (
    <Placard title="بطاقة الطيّار">
      <div className="flex items-center gap-4">
        <HexIcon size={56} glyph="M24 38 L32 28 L40 38" filled label={`شارة رتبة ${deck.rank.name}`} />
        <div className="min-w-0">
          <bdi ref={hoursRef} dir="ltr" className="num block text-[32px] leading-none font-extrabold text-(--color-accent)">
            0.00
          </bdi>
          <p className="mt-1 text-[13px] text-(--color-text-dim)">{deck.rank.name}</p>
        </div>
      </div>
    </Placard>
  )
}

function NextRankCard({ deck }: { deck: DeckData }) {
  if (!deck.next_rank) {
    return (
      <Placard title="الرتبة">
        <p className="text-[15px] text-(--color-accent)">بلغتَ أعلى رتبة.</p>
        <p className="mt-1 text-[13px] text-(--color-text-dim)">لا رتبة بعدها — ساعاتك تُسجَّل وتبقى في سجلّك.</p>
      </Placard>
    )
  }
  const next = deck.next_rank
  return (
    <Placard title="نحو الرتبة التالية" aside={next.name}>
      <div className="mb-2 flex items-baseline justify-between gap-3 text-[13px]">
        <span className="text-(--color-text-dim)">
          عند <bdi dir="ltr">{fmtDecimal(next.at_hours)}</bdi> ساعة
        </span>
        <span>
          بقي <bdi dir="ltr">{fmtDecimal(next.remaining)}</bdi>
        </span>
      </div>
      <ProgressBar pct={next.progress_pct} />
      <p className="mt-1.5 text-[12px] text-(--color-text-dim)">
        <bdi dir="ltr">{next.progress_pct}%</bdi> من هذه الشريحة
      </p>
    </Placard>
  )
}

function DeckCard({ deck }: { deck: DeckData }) {
  return (
    <div className="flex flex-col gap-3.5">
      <Hero deck={deck} />
      <NextRankCard deck={deck} />

      <Placard title="حالة الطيران">
        <Prow label="الحالة" value={deck.flight.grounded ? 'أرضي' : 'طائر'} tone={deck.flight.grounded ? 'red' : 'green'} />
        <Prow label="آخر نشاط" value={formatDay(deck.flight.last_activity_on) ?? 'لا نشاط بعد'} />
        <p className="pt-2 text-[13px] text-(--color-text-dim)">
          {deck.flight.grounded ? 'سجّل قراءةً أو حفظًا جديدًا لتعود إلى الجوّ.' : 'واصل، ونشاطك محسوب.'}
        </p>
      </Placard>

      <Placard title="السرب">
        {deck.team ? (
          <>
            <Prow label="الاسم" value={deck.team.name} />
            <Prow label="ترتيبه" value={deck.team.rank_in_org ?? 'غير متاح بعد'} />
          </>
        ) : (
          <p className="text-[14px] text-(--color-text-dim)">لست في سرب حاليًّا. راجع المشرف.</p>
        )}
      </Placard>
    </div>
  )
}

export default function Deck() {
  const deckState = useAsync(() => api.me.deck(), [])
  const eventsState = useAsync(() => api.me.events(10), [])

  return (
    <div className="flex flex-col gap-3.5">
      <Async state={deckState} loadingTitle="بطاقة الطيّار">
        {(deck) => <DeckCard deck={deck} />}
      </Async>

      <Async state={eventsState} loadingTitle="سجلّ ساعاتي">
        {(data) =>
          data.events.length ? (
            <Placard title="سجلّ ساعاتي" aside={`آخر ${data.events.length}`}>
              {data.events.map((e) => (
                <div key={e.id}>
                  <FeedRow
                    tone={e.kind === 'correction' ? 'red' : 'accent'}
                    icon={e.kind === 'correction' ? WARN : CHECK}
                    text={
                      <span>
                        {KINDS[e.kind] ?? e.kind} <bdi dir="ltr">({e.delta})</bdi>
                      </span>
                    }
                    time={formatDay(e.occurred_on)}
                  />
                  {e.reason ? <p className="mb-1.5 text-[12px] text-(--color-red-text)">{e.reason}</p> : null}
                </div>
              ))}
            </Placard>
          ) : (
            <Placard title="سجلّ ساعاتي">
              <p className="py-2 text-[14px] text-(--color-text-dim)">لا أحداث بعد. أوّل إنجاز يبدأ سجلّك.</p>
            </Placard>
          )
        }
      </Async>
    </div>
  )
}
