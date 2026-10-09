import { useMemo, useState } from 'react'

import { api, ApiError } from '../../api'
import type { PasteCommitResult, PastePreview, PastePreviewRow } from '../../api/types/paste'
import type { StudentRef } from '../../api/types/quran'
import { useAsync } from '../../state/useAsync'
import { Async } from '../../ui/Async'
import Button from '../../ui/Button'
import type { Column } from '../../ui/DataTable'
import DataTable from '../../ui/DataTable'
import Field, { fieldClass } from '../../ui/Field'
import Placard from '../../ui/Placard'
import Prow from '../../ui/Prow'
import ErrorText from '../../ui/ErrorText'

/**
 * استيراد راصد — `POST /admin/paste/{preview,commit}` (FR-030..034/040).
 * **الاسم في المسارات تاريخيّ لا وظيفيّ** — رفع ملفّ لا مربّع لصق نصّ
 * (`و-٥.md §٢` قرار #١٠). كل نسبة تصل نصًّا محسوبًا من الخادم — لا حساب
 * هنا، وحالة المطابقة تُقارَن بالمساواة النصّية فقط لا رقمًا (`AGENTS.md` ٥).
 * **`value_overrides` بلا واجهة عمدًا** — قرار و-٥ الموروث (`و-١٨.md §١.٢`).
 */
const STATUS_LABEL: Record<string, string> = { matched: 'مطابَق', ambiguous: 'تطابق متعدّد', unmatched: 'غير مطابَق' }

/**
 * «ما سيُكتب» — تُعرَض **قبل** زرّ الاعتماد لا بعده.
 *
 * الخادم يبني خطّة الاستيراد مرّة واحدة ويستعملها للمعاينة وللتنفيذ معًا
 * (`services/paste._plan_rows`)، فهذه الأرقام ليست تقديرًا بل هي الخطّة
 * نفسها. كلّها تصل محسوبةً — لا حساب هنا (`AGENTS.md` ٥).
 */
function PlanSummary({ preview }: { preview: PastePreview }) {
  const t = preview.totals
  return (
    <Placard title="ما سيُكتب" aside={`${t.events_new} حدثًا جديدًا`}>
      <Prow label="صفوف الطلاب في الملفّ" value={<bdi dir="ltr">{t.rows}</bdi>} />
      <Prow label="جاهزة للاستيراد" value={<bdi dir="ltr">{t.rows_resolved}</bdi>} />
      {t.rows_needing_attention ? (
        <Prow
          label="تحتاج انتباهك — لن تُستورَد بلا حلّ"
          value={<bdi dir="ltr">{t.rows_needing_attention}</bdi>}
          tone="red"
        />
      ) : null}
      <Prow label="أحداث جديدة ستُضاف" value={<bdi dir="ltr">{t.events_new}</bdi>} tone="accent" />
      {t.events_already_imported ? (
        <Prow
          label="مستبعَد لأنّه استُورد سابقًا"
          value={<bdi dir="ltr">{t.events_already_imported}</bdi>}
        />
      ) : null}
      {t.events_skipped_zero ? (
        <Prow label="صفرٌ لا يُنشئ حدثًا" value={<bdi dir="ltr">{t.events_skipped_zero}</bdi>} />
      ) : null}
      <Prow label="مجموع الساعات" value={<bdi dir="ltr">{t.hours_total}</bdi>} tone="accent" />

      {preview.excluded_labels.length ? (
        <p className="pt-2 text-[12px] text-(--color-text-dim)">
          استُبعد من الملفّ: {preview.excluded_labels.join(' · ')} — صفوف تلخيصٍ لا طلّاب.
        </p>
      ) : null}

      <p className="pt-2 text-[12px] text-(--color-text-dim)">
        النسب تُحتسب هنا من المستهدف والمنجز، وتجاوز ١٠٠٪ يُحتسب كما هو. لذلك يختلف مجموعنا عن
        عمود «الإجمالي» في ملفّ راصد، فهو متوسّطٌ يقصّ كل نسبة عند ١٠٠٪.
      </p>
    </Placard>
  )
}

const pct = (value: string) => <bdi dir="ltr">{value}%</bdi>

/**
 * سبعة أعمدة — **أسوأ حالة في المستودع**، فهُوجرت أوّلًا: إن لاءمت فالبقيّة
 * تلائم. فوق ١٠٢٤px جدول، وتحته بطاقةٌ لكل طالب باسمه عنوانًا.
 *
 * و`columns` تُبنى داخل المكوّن بـ`useMemo` لأن خلايا الحلّ اليدويّ تُغلق على
 * المُعالِج — بخلاف الجداول الساكنة التي تُعرَّف مرّةً في نطاق الوحدة.
 */
function PreviewTable({
  rows,
  students,
  resolutions,
  onResolve,
}: {
  rows: PastePreviewRow[]
  students: StudentRef[]
  resolutions: Record<string, string>
  onResolve: (name: string, userId: string | null) => void
}) {
  const columns = useMemo<Column<PastePreviewRow>[]>(
    () => [
      { id: 'name', header: 'الطالب', cell: (r) => r.name, primary: true },
      { id: 'hifz', header: 'حفظ', numeric: true, cell: (r) => pct(r.percentages.hifz) },
      { id: 'thabat', header: 'تثبيت', numeric: true, cell: (r) => pct(r.percentages.thabat) },
      {
        id: 'muraja3a',
        header: 'مراجعة',
        numeric: true,
        cell: (r) => pct(r.percentages.muraja3a),
      },
      {
        id: 'attendance',
        header: 'الحضور',
        numeric: true,
        // عددٌ من أيام التسميع لا حاضر/غائب — هكذا يصل من راصد فعلًا.
        cell: (r) => (
          <>
            <bdi dir="ltr">{r.attendance}</bdi> من <bdi dir="ltr">{r.tasmi3_days}</bdi>
          </>
        ),
      },
      {
        id: 'status',
        header: 'المطابقة',
        cell: (r) => (
          <span className={r.match_status === 'matched' ? '' : 'text-(--color-red-text)'}>
            {STATUS_LABEL[r.match_status] ?? r.match_status}
          </span>
        ),
      },
    ],
    []
  )

  return (
    <DataTable
      columns={columns}
      rows={rows}
      rowKey={(r) => r.name}
      caption="كل الطلاب في الملفّ"
      empty="لا صفوف طلّاب في هذا الملفّ."
      action={(r) =>
        r.match_status === 'matched' ? null : (
          <select
            aria-label={`اختر الطالب الصحيح لـ${r.name}`}
            value={resolutions[r.name] ?? ''}
            onChange={(e) => onResolve(r.name, e.target.value || null)}
            className="min-h-[44px] w-full rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) px-2 text-[13px] text-(--color-text)"
          >
            <option value="">بلا اختيار — لن يُستورَد</option>
            {students.map((st) => (
              <option key={st.id} value={st.id}>
                {st.full_name}
              </option>
            ))}
          </select>
        )
      }
    />
  )
}

function PreviewBody({
  preview,
  onCommit,
}: {
  preview: PastePreview
  onCommit: (resolutions: Record<string, string>) => Promise<PasteCommitResult>
}) {
  const [resolutions, setResolutions] = useState<Record<string, string>>({})
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  function resolve(name: string, userId: string | null) {
    setResolutions((prev) => {
      const next = { ...prev }
      if (userId !== null) next[name] = userId
      else delete next[name]
      return next
    })
  }

  const unresolved = preview.rows.filter((r) => r.match_status !== 'matched' && resolutions[r.name] === undefined)

  async function commit() {
    setBusy(true)
    setError('')
    try {
      await onCommit(resolutions)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  const studentsState = useAsync(() => api.admin.quranStudents(), [])

  return (
    <Async state={studentsState} loadingTitle="استيراد راصد">
      {(studentsData) => (
        <div className="flex flex-col gap-3.5">
          {preview.duplicate_warning ? (
            <Placard title="تحذير">
              <p className="py-2 text-[14px] text-(--color-red-text)">
                يبدو أن هذا الملفّ استُورد من قبل بتاريخ {preview.duplicate_imported_at} — يمكنك المتابعة إن كنت متعمّدًا.
              </p>
            </Placard>
          ) : null}

          {preview.weights_missing ? (
            <Placard title="لا أوزان سارية">
              <p className="py-2 text-[14px] text-(--color-red-text)">
                لا توجد نسخة أوزان سارية لهذا التاريخ، فلن تُحتسب أيّ ساعة. اضبط الأوزان أوّلًا من
                شاشة «الأوزان» ثم أعد المعاينة.
              </p>
            </Placard>
          ) : null}

          <PlanSummary preview={preview} />

          <PreviewTable
            rows={preview.rows}
            students={studentsData.students}
            resolutions={resolutions}
            onResolve={resolve}
          />

          {error ? <ErrorText spacing="">{error}</ErrorText> : null}

          <Button disabled={busy} onClick={commit} className="w-full">
            {busy ? 'جارٍ الاعتماد…' : unresolved.length ? `اعتماد الاستيراد (سيُستبعَد ${unresolved.length} بلا حلّ)` : 'اعتماد الاستيراد'}
          </Button>
        </div>
      )}
    </Async>
  )
}

export default function RasdImport() {
  const [file, setFile] = useState<File | null>(null)
  const [occurredOn, setOccurredOn] = useState('')
  const [preview, setPreview] = useState<PastePreview | null>(null)
  const [commitResult, setCommitResult] = useState<PasteCommitResult | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  function pickFile(e: React.ChangeEvent<HTMLInputElement>) {
    setFile(e.target.files?.[0] ?? null)
    setPreview(null)
    setCommitResult(null)
  }

  async function doPreview() {
    if (!file) return
    setBusy(true)
    setError('')
    setCommitResult(null)
    try {
      setPreview(await api.admin.pastePreview(file, occurredOn))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  // الملفّ والتاريخ يُعادان هنا لا في `PreviewBody` — `pasteCommit` يحتاجهما
  // مجدَّدًا (الطلب الثاني مستقلّ عن الأوّل)، والشاشة الأمّ وحدها تملكهما.
  async function commit(resolutions: Record<string, string>) {
    if (!file) throw new ApiError(0, 'لا ملفّ محمَّل.')
    const result = await api.admin.pasteCommit(file, occurredOn, resolutions)
    setCommitResult(result)
    setPreview(null)
    return result
  }

  return (
    <div className="flex flex-col gap-3.5">

      <Placard title="رفع الملفّ">
        <Field label="ملفّ CSV من راصد" htmlFor="rasd_file">
          <input id="rasd_file" type="file" accept=".csv" onChange={pickFile} className={fieldClass} />
        </Field>
        <Field label="تاريخ الوقوع" htmlFor="rasd_date">
          <input id="rasd_date" type="date" value={occurredOn} onChange={(e) => setOccurredOn(e.target.value)} className={fieldClass} />
        </Field>

        {error ? <ErrorText>{error}</ErrorText> : null}

        <Button disabled={busy || !file || !occurredOn} onClick={doPreview} className="w-full">
          {busy ? 'جارٍ المعاينة…' : 'معاينة'}
        </Button>
      </Placard>

      {preview ? <PreviewBody preview={preview} onCommit={commit} /> : null}

      {commitResult ? (
        <Placard title="نتيجة الاستيراد" aside={`${commitResult.events_created} حدثًا جديدًا`}>
          {commitResult.rows.map((row) => (
            <div key={row.name} className="mb-2 border-b border-(--color-border) pb-2 last:border-none">
              <Prow label={row.name} value={row.status} />
            </div>
          ))}
        </Placard>
      ) : null}
    </div>
  )
}
