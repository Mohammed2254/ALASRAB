import { api, ApiError } from '../../api'
import type { QuestionRow } from '../../api/types/dailyQuestion'
import { useAsync } from '../../state/useAsync'
import { Async } from '../../ui/Async'
import type { Column } from '../../ui/DataTable'
import DataTable from '../../ui/DataTable'
import Pill from '../../ui/Pill'
import NewQuestionForm from './NewQuestionForm'

/**
 * سؤال اليوم — `GET/POST/DELETE /admin/questions*` (و-٢١ · FR-060).
 *
 * **الشاشة التي لم تكن:** `SCOPE.md` ط-٦ أعلن صراحةً أن «لا مسار إنشاء
 * إداريًّا» والصفوف تُدرَج «بذرة أو SQL». وأثرُ ذلك على خادمٍ منشور أن
 * الجمعية الجديدة بلا سؤالٍ واحد إلى الأبد، فشاشةُ «سؤال اليوم» للطيّار
 * **ميتةٌ بالتصميم** — وهو ما لا يصحّ في بندٍ MUST.
 *
 * **و«مُقفَل» حقلٌ من الخادم لا استنتاجٌ هنا**: سؤالٌ أُجيب لا يُعدَّل ولا
 * يُحذَف، لأن `answers.correct` و`point_event_id` لا يفترقان بقيدٍ في
 * القاعدة (ث-١٧) وقد كُتبا معًا — فتغييرُ الصحيح بعد الإجابة يجعل إجابةً
 * صحيحةً تبدو خاطئة وقد دُفعت ساعاتُها فعلًا.
 */
const dayFormatter = new Intl.DateTimeFormat('ar-SA-u-ca-gregory-nu-latn', {
  day: 'numeric',
  month: 'long',
  timeZone: 'Asia/Riyadh',
})
const formatDay = (iso: string) => dayFormatter.format(new Date(`${iso}T00:00:00Z`))

/** نصُّ الخيار الصحيح — يُعرض لأن رقم المعرّف لا يقرؤه أحد. */
const correctText = (q: QuestionRow) =>
  q.choices.find((c) => c.id === q.correct_id)?.text ?? '—'

export default function DailyQuestions() {
  const state = useAsync(() => api.admin.questions(), [])

  async function remove(row: QuestionRow) {
    try {
      await api.admin.deleteQuestion(row.id)
      state.reload()
    } catch (err) {
      // رسالة الخادم كما وصلت: هو من يعرف عدد من أجاب، لا هذه الشاشة.
      window.alert(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    }
  }

  const columns: Column<QuestionRow>[] = [
    { id: 'prompt', header: 'السؤال', cell: (q) => q.prompt, primary: true },
    { id: 'day', header: 'اليوم', cell: (q) => formatDay(q.day) },
    { id: 'correct', header: 'الجواب الصحيح', cell: (q) => correctText(q) },
    {
      id: 'reward',
      header: 'المكافأة',
      numeric: true,
      cell: (q) => <bdi dir="ltr">{q.reward_hours}</bdi>,
    },
    {
      id: 'state',
      header: 'الحالة',
      cell: (q) =>
        q.locked ? (
          <Pill tone="muted">
            أجاب <bdi dir="ltr">{q.answers}</bdi>
          </Pill>
        ) : (
          // الأخضر مأذون: «لم يُجَب بعد» حالةٌ **نشطة** — السؤال ما زال
          // قابلًا للتعديل والحذف (`VISUAL.md §٢`).
          <Pill tone="green">نشط</Pill>
        ),
    },
  ]

  return (
    <div className="flex flex-col gap-3.5">
      <Async state={state} loadingTitle="سؤال اليوم">
        {(data) => (
          <DataTable
            columns={columns}
            rows={data.questions}
            rowKey={(q) => q.id}
            caption="الأسئلة"
            empty="لا أسئلة بعد — أضِف سؤالًا أدناه، وإلّا بقيت شاشة الطالب فارغة."
            action={(row) =>
              row.locked ? (
                <span className="text-[12px] text-(--color-text-dim)">
                  أُجيب — لا يُعدَّل ولا يُحذَف
                </span>
              ) : (
                <button
                  type="button"
                  onClick={() => remove(row)}
                  className="min-h-[44px] shrink-0 rounded-(--radius-sm) border border-(--color-border-strong) px-3 text-[13px] text-(--color-text-dim)"
                >
                  حذف
                </button>
              )
            }
          />
        )}
      </Async>

      <NewQuestionForm onCreated={state.reload} />
    </div>
  )
}
