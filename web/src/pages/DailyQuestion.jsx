import { useState } from 'react'

import Placard, { Row } from '../components/Placard'
import { Async } from '../components/States'
import { api } from '../lib/api'
import { useAsync } from '../state/useAsync'

/*
  السؤال اليومي — و-٩ج · FR-060.

  **الصحيح وشرحه يظهران دائمًا** — بعد الإجابة الخاطئة كما الصحيحة، وحتى
  بعد إعادة فتح الشاشة (`answered` يصل من الخادم، لا يُخزَّن هنا). إعادة
  الجلب بعد الإرسال (`state.reload`) هي مصدر الحقيقة الوحيد — لا حالة محليّة
  توازي ردّ الخادم.
*/

export default function DailyQuestion({ onDone }) {
  const state = useAsync(() => api.todayQuestion(), [])

  return (
    <div className="taxi-in mx-auto w-full max-w-[520px] px-4 pt-6 pb-10">
      <header className="mb-5 flex items-baseline gap-3">
        <h1 className="font-display text-[26px] leading-none">سؤال اليوم</h1>
        <span className="centerline" />
        <button
          type="button"
          onClick={onDone}
          className="min-h-[44px] shrink-0 px-2 text-[13px] text-muted"
        >
          رجوع
        </button>
      </header>

      <Async state={state} loadingTitle="سؤال اليوم">
        {(data) => <Body question={data.question} onAnswered={state.reload} />}
      </Async>
    </div>
  )
}

function Body({ question, onAnswered }) {
  if (!question) {
    return (
      <Placard title="سؤال اليوم">
        <p className="py-2 text-[14px] text-muted">لا سؤال اليوم بعد.</p>
      </Placard>
    )
  }
  return question.answered ? (
    <Result question={question} answered={question.answered} />
  ) : (
    <ChoiceForm question={question} onAnswered={onAnswered} />
  )
}

function ChoiceForm({ question, onAnswered }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function pick(choiceId) {
    setBusy(true)
    setError('')
    try {
      await api.answerQuestion(question.id, choiceId)
      onAnswered()
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <Placard title={question.prompt}>
      <div className="flex flex-col gap-2">
        {question.choices.map((choice) => (
          <button
            key={choice.id}
            type="button"
            disabled={busy}
            onClick={() => pick(choice.id)}
            className="min-h-[44px] w-full border border-concrete/45 px-3 text-[14px] text-paint disabled:opacity-50"
          >
            {choice.text}
          </button>
        ))}
      </div>
      {error && <p className="mt-3 text-[13px] text-hold">{error}</p>}
    </Placard>
  )
}

function Result({ question, answered }) {
  return (
    <Placard title={question.prompt} aside={answered.correct ? 'إجابة صحيحة' : 'إجابة خاطئة'}>
      <div className="flex flex-col gap-1">
        {question.choices.map((choice) => {
          const isChosen = choice.id === answered.choice_id
          const isCorrect = choice.id === answered.correct_id
          const tone = isCorrect ? 'taxi' : isChosen ? 'hold' : 'muted'
          return (
            <Row
              key={choice.id}
              label={choice.text}
              value={isCorrect ? 'الصحيحة' : isChosen ? 'اخترتها' : ''}
              tone={tone}
            />
          )
        })}
      </div>
      <p className="mt-3 text-[13px] text-muted">{answered.note}</p>
      <Row label="المكافأة" value={<bdi dir="ltr">{answered.awarded_hours}</bdi>} tone="taxi" />
    </Placard>
  )
}
