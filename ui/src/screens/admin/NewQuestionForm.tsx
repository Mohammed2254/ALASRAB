import { useState } from 'react'

import { api, ApiError } from '../../api'
import type { QuestionForm } from '../../api/types/dailyQuestion'
import Button from '../../ui/Button'
import Field from '../../ui/Field'
import Placard from '../../ui/Placard'

/**
 * إنشاء سؤال اليوم — `POST /admin/questions` (و-٢١ · FR-060).
 *
 * **أربع خانات ثابتة لا قائمةٌ تنمو**، ومعرّفاتها `1..4` مكتوبةٌ لا محسوبة:
 * قائمةٌ بزرّ «أضف خيارًا» تحتاج حساب المعرّف التالي، و**الحساب في الواجهة
 * ممنوع** (بوّابة AST) — ومحقٌّ أن يُمنع هنا تحديدًا، لأن معرّفًا مكرَّرًا
 * يُنتج سؤالًا بإجابتين صحيحتين. والفارغةُ تُرشَّح في طبقة الـAPI.
 *
 * والحدّ أربعة لأن بطاقة الطالب تعرضها عمودًا واحدًا على عرض ٣٢٠px،
 * والخامس يُخرجها عن المنفذ.
 */
const fieldClass =
  'min-h-[48px] w-full rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) px-3 text-[16px] text-(--color-text)'

const SLOTS = [1, 2, 3, 4] as const

const EMPTY: QuestionForm = {
  day: '',
  prompt: '',
  choices: SLOTS.map((id) => ({ id, text: '' })),
  correct_id: '',
  note: '',
  reward_hours: '1.00',
}

export default function NewQuestionForm({ onCreated }: { onCreated: () => void }) {
  const [form, setForm] = useState<QuestionForm>(EMPTY)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const set = <K extends keyof QuestionForm>(key: K, value: QuestionForm[K]) =>
    setForm((f) => ({ ...f, [key]: value }))

  const setChoice = (id: number, text: string) =>
    setForm((f) => ({
      ...f,
      choices: f.choices.map((c) => (c.id === id ? { ...c, text } : c)),
    }))

  // الصالح: خانةٌ فيها نصّ. و**الزرّ معطَّل حتى يختار المشرف الصحيحة** — سؤالٌ
  // بلا إجابة صحيحة يُخطئ فيه كلُّ من يجيب، والخادم يرفضه فلا نُرسله أصلًا.
  const filled = form.choices.filter((c) => c.text.trim())
  const chosenHasText = filled.some((c) => String(c.id) === form.correct_id)

  async function submit() {
    setBusy(true)
    setError('')
    try {
      await api.admin.createQuestion(form)
      setForm(EMPTY)
      onCreated()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Placard title="سؤال جديد" aside="سؤال واحد لكل يوم">
      <Field label="اليوم" htmlFor="q_day">
        <input
          id="q_day"
          type="date"
          value={form.day}
          onChange={(e) => set('day', e.target.value)}
          className={fieldClass}
        />
      </Field>

      <Field label="نصّ السؤال" htmlFor="q_prompt">
        <textarea
          id="q_prompt"
          rows={2}
          value={form.prompt}
          onChange={(e) => set('prompt', e.target.value)}
          className={`${fieldClass} min-h-[72px] py-2 leading-7`}
        />
      </Field>

      <fieldset className="mb-3">
        <legend className="mb-1.5 text-[13px] text-(--color-text-dim)">
          الخيارات — اترك ما لا تحتاجه فارغًا، وحدِّد الصحيح
        </legend>
        {form.choices.map((choice) => (
          <div key={choice.id} className="mb-2 flex items-center gap-2">
            {/* **المُدخَل نفسه يملأ الـ٤٤px، لا التسمية حوله.**
                كُتب أوّلًا بـ`size-5` وتسميةٍ بـ`min-h-[44px]`، فأمسكه القياس
                البصريّ: ق-١٤ يقيس **عنصر الإدخال** لا الصندوق الذي يحويه —
                ومحقٌّ، فالإصبع تضرب العنصر لا والده. فصار `absolute inset-0`
                شفّافًا يغطّي التسمية كاملةً: مساحةُ اللمس حقيقيةٌ ومقيسة، لا
                مزعومةً في تعليق.

                و`appearance-none` تُلغي الدائرة الأصلية، فالمؤشّر المرئيّ
                شقيقٌ يقوده `peer-checked` — ومعه حلقةُ تركيزٍ صريحة، وإلّا
                ضاع التنقّل بلوحة المفاتيح مع المظهر. */}
            <label className="relative flex min-h-[44px] shrink-0 cursor-pointer items-center gap-2 px-1">
              <input
                type="radio"
                name="q_correct"
                aria-label={`الجواب الصحيح هو الخيار ${choice.id}`}
                value={choice.id}
                checked={String(choice.id) === form.correct_id}
                onChange={(e) => set('correct_id', e.target.value)}
                className="peer absolute inset-0 size-full cursor-pointer appearance-none"
              />
              <span
                aria-hidden="true"
                className="size-4 shrink-0 rounded-full border-2 border-(--color-border-strong) peer-checked:border-(--color-accent) peer-checked:bg-(--color-accent) peer-focus-visible:ring-2 peer-focus-visible:ring-(--color-accent)"
              />
              <span className="text-[13px] text-(--color-text-dim) peer-checked:text-(--color-accent)">
                الصحيح
              </span>
            </label>
            <input
              aria-label={`نصّ الخيار ${choice.id}`}
              value={choice.text}
              onChange={(e) => setChoice(choice.id, e.target.value)}
              className={`${fieldClass} min-w-0 flex-1`}
            />
          </div>
        ))}
      </fieldset>

      <Field label="شرح الجواب — يظهر للطالب صحّت إجابته أم لا" htmlFor="q_note">
        <textarea
          id="q_note"
          rows={2}
          value={form.note}
          onChange={(e) => set('note', e.target.value)}
          className={`${fieldClass} min-h-[72px] py-2 leading-7`}
        />
      </Field>

      <Field label="ساعات المكافأة على الإجابة الصحيحة" htmlFor="q_reward">
        <input
          id="q_reward"
          inputMode="decimal"
          value={form.reward_hours}
          onChange={(e) => set('reward_hours', e.target.value)}
          className={fieldClass}
        />
      </Field>

      {error ? (
        <p role="alert" className="mb-3 text-[13px] text-(--color-red-text)">
          {error}
        </p>
      ) : null}

      <Button
        disabled={busy || !form.day || !form.prompt.trim() || !form.note.trim() || !chosenHasText}
        onClick={submit}
        className="w-full"
      >
        {busy ? 'جارٍ الحفظ…' : 'حفظ السؤال'}
      </Button>
    </Placard>
  )
}
