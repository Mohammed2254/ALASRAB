import { useState } from 'react'

import { api, ApiError } from '../api'
import { fmtDecimal } from '../api/format'
import type { Answered, Question } from '../api/types/engagement'
import { go } from '../nav/history'
import { useAsync } from '../state/useAsync'
import { Async } from '../ui/Async'
import EmptyState from '../ui/EmptyState'
import Pill from '../ui/Pill'
import Placard from '../ui/Placard'
import Prow from '../ui/Prow'
import Subback from '../ui/Subback'
import ErrorText from '../ui/ErrorText'

/**
 * سؤال اليوم — `GET /questions/today` · `POST /questions/{id}/answer` (FR-060).
 * **الصحيح وشرحه يظهران دائمًا** — بعد الإجابة الخاطئة كما الصحيحة، وحتى بعد
 * إعادة فتح الشاشة (`answered` يصل من الخادم، لا يُخزَّن هنا). `state.reload`
 * بعد الإرسال هو مصدر الحقيقة الوحيد — لا حالة محليّة توازي ردّ الخادم.
 */

function ChoiceForm({ question, onAnswered }: { question: Question; onAnswered: () => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function pick(choiceId: number) {
    setBusy(true)
    setError('')
    try {
      await api.engagement.answerQuestion(question.id, choiceId)
      onAnswered()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
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
            className="min-h-[44px] w-full rounded-(--radius-sm) border border-(--color-border-strong) px-3 text-[14px] text-(--color-text) disabled:opacity-50"
          >
            {choice.text}
          </button>
        ))}
      </div>
      {error ? <ErrorText spacing="mt-3">{error}</ErrorText> : null}
    </Placard>
  )
}

function Result({ question, answered }: { question: Question; answered: Answered }) {
  return (
    <Placard title={question.prompt} aside={answered.correct ? 'إجابة صحيحة' : 'إجابة خاطئة'}>
      <div className="flex flex-col">
        {question.choices.map((choice) => {
          const isChosen = choice.id === answered.choice_id
          const isCorrect = choice.id === answered.correct_id
          return (
            <Prow
              key={choice.id}
              label={choice.text}
              value={isCorrect ? 'الصحيحة' : isChosen ? 'اخترتها' : ''}
              tone={isCorrect ? 'accent' : isChosen ? 'red' : undefined}
            />
          )
        })}
      </div>
      <p className="mt-3 text-[13px] text-(--color-text-dim)">{answered.note}</p>
      <Prow label="المكافأة" value={<bdi dir="ltr">{fmtDecimal(answered.awarded_hours)}</bdi>} tone="accent" />

      {/* «سلسلتك المتتالية» — كما في النموذج، وتظهر بعد الإجابة لا قبلها.
          والعدد يصل محسوبًا من الخادم. */}
      {answered.streak ? (
        <div className="mt-3 text-center">
          <Pill tone="accent">
            سلسلتك المتتالية — <bdi dir="ltr">{answered.streak}</bdi> يوم
          </Pill>
        </div>
      ) : null}
    </Placard>
  )
}

export default function DailyQuestion() {
  const state = useAsync(() => api.engagement.todayQuestion(), [])

  return (
    <div className="flex flex-col gap-3.5">
      <Subback label="الرئيسية" onClick={() => go('deck')} />
      <Async state={state} loadingTitle="سؤال اليوم">
        {(data) => {
          if (!data.question) {
            return (
              <Placard title="سؤال اليوم">
                <EmptyState>لا سؤال اليوم بعد.</EmptyState>
              </Placard>
            )
          }
          return data.question.answered ? (
            <Result question={data.question} answered={data.question.answered} />
          ) : (
            <ChoiceForm question={data.question} onAnswered={state.reload} />
          )
        }}
      </Async>
    </div>
  )
}
