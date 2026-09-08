import { useState } from 'react'

import Placard, { Row } from '../../components/Placard'
import { Async } from '../../components/States'
import { api } from '../../lib/api'
import { useAsync } from '../../state/useAsync'

/*
  استيراد راصد — و-٥ · FR-030..034/040.

  **الاسم في المسارات تاريخيّ** (`/admin/paste/*`) لا وظيفيّ — الشاشة ترفع
  ملفًّا لا تعرض مربّع لصق نصّ (`docs/slices/و-٥.md` §٢ قرار #١٠).

  **كل نسبة وساعة تصل محسوبة من الخادم** — لا حساب هنا (AGENTS ٥). حالة
  المطابقة (`matched`/`ambiguous`/`unmatched`) نصٌّ يُقارَن بالمساواة فقط،
  لا رقم مجال.
*/

const STATUS_LABEL = {
  matched: 'مطابَق',
  ambiguous: 'تطابق متعدّد',
  unmatched: 'غير مطابَق',
}

export default function RasdImport({ onDone }) {
  const studentsState = useAsync(() => api.quranStudents(), [])

  const [file, setFile] = useState(null)
  const [occurredOn, setOccurredOn] = useState('')
  const [preview, setPreview] = useState(null)
  const [resolutions, setResolutions] = useState({})
  const [commitResult, setCommitResult] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  function pickFile(e) {
    setFile(e.target.files[0] ?? null)
    setPreview(null)
    setCommitResult(null)
    setResolutions({})
  }

  async function doPreview() {
    setBusy(true)
    setError('')
    setCommitResult(null)
    try {
      setPreview(await api.pastePreview(file, occurredOn))
      setResolutions({})
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function doCommit() {
    setBusy(true)
    setError('')
    try {
      setCommitResult(await api.pasteCommit(file, occurredOn, resolutions))
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  function resolve(name, value) {
    setResolutions((prev) => {
      const next = { ...prev }
      if (value) next[name] = Number(value)
      else delete next[name]
      return next
    })
  }

  const unresolved = preview
    ? preview.rows.filter((r) => r.match_status !== 'matched' && !resolutions[r.name])
    : []

  return (
    <div className="taxi-in mx-auto w-full max-w-[520px] px-4 pt-6 pb-10">
      <header className="mb-5 flex items-baseline gap-3">
        <h1 className="font-display text-[26px] leading-none">استيراد راصد</h1>
        <span className="centerline" />
        <button
          type="button"
          onClick={onDone}
          className="min-h-[44px] shrink-0 px-2 text-[13px] text-muted"
        >
          رجوع
        </button>
      </header>

      <Placard title="رفع الملفّ">
        <label htmlFor="rasd_file" className="mb-1.5 block text-[13px]">
          ملفّ CSV من راصد
        </label>
        <input
          id="rasd_file"
          type="file"
          accept=".csv"
          onChange={pickFile}
          className="mb-3 min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
        />

        <label htmlFor="rasd_date" className="mb-1.5 block text-[13px]">
          تاريخ الوقوع
        </label>
        <input
          id="rasd_date"
          type="date"
          value={occurredOn}
          onChange={(e) => setOccurredOn(e.target.value)}
          className="mb-3 min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
        />

        {error && (
          <p role="alert" className="mb-3 text-[13px] text-hold">
            {error}
          </p>
        )}

        <button
          type="button"
          disabled={busy || !file || !occurredOn}
          onClick={doPreview}
          className="min-h-[48px] w-full border border-taxi bg-taxi text-[16px] text-asphalt disabled:opacity-40"
        >
          {busy ? 'جارٍ المعاينة…' : 'معاينة'}
        </button>
      </Placard>

      {preview && (
        <Async state={studentsState} loadingTitle="استيراد راصد">
          {(studentsData) => (
            <div className="mt-4 flex flex-col gap-4">
              {preview.duplicate_warning && (
                <Placard title="تحذير">
                  <p className="py-2 text-[14px] text-hold">
                    يبدو أن هذا الملفّ استُورد من قبل بتاريخ {preview.duplicate_imported_at} —
                    يمكنك المتابعة إن كنت متعمّدًا.
                  </p>
                </Placard>
              )}

              {preview.rows.map((row) => (
                <Placard key={row.name} title={row.name} aside={STATUS_LABEL[row.match_status]}>
                  <Row label="حفظ" value={<bdi dir="ltr">{row.percentages.hifz}%</bdi>} />
                  <Row label="تثبيت" value={<bdi dir="ltr">{row.percentages.thabat}%</bdi>} />
                  <Row label="مراجعة" value={<bdi dir="ltr">{row.percentages.muraja3a}%</bdi>} />
                  <Row label="الحضور" value={<bdi dir="ltr">{row.attendance}</bdi>} />

                  {row.match_status !== 'matched' && (
                    <div className="mt-2 border-t border-concrete/35 pt-2">
                      <label htmlFor={`resolve_${row.name}`} className="mb-1.5 block text-[13px]">
                        اختر الطالب الصحيح — لن يُستورَد بلا اختيار
                      </label>
                      <select
                        id={`resolve_${row.name}`}
                        value={resolutions[row.name] ?? ''}
                        onChange={(e) => resolve(row.name, e.target.value)}
                        className="min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
                      >
                        <option value="">بلا اختيار</option>
                        {studentsData.students.map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.full_name}
                          </option>
                        ))}
                      </select>
                    </div>
                  )}
                </Placard>
              ))}

              <button
                type="button"
                disabled={busy}
                onClick={doCommit}
                className="min-h-[48px] w-full border border-taxi bg-taxi text-[16px] text-asphalt disabled:opacity-40"
              >
                {busy
                  ? 'جارٍ الاعتماد…'
                  : unresolved.length
                    ? `اعتماد الاستيراد (سيُستبعَد ${unresolved.length} بلا حلّ)`
                    : 'اعتماد الاستيراد'}
              </button>
            </div>
          )}
        </Async>
      )}

      {commitResult && (
        <Placard title="نتيجة الاستيراد" aside={`${commitResult.events_created} حدثًا جديدًا`}>
          {commitResult.rows.map((row) => (
            <div key={row.name} className="mb-2 border-b border-concrete/35 pb-2 last:border-0">
              <Row label={row.name} value={row.status} />
            </div>
          ))}
        </Placard>
      )}
    </div>
  )
}
