import { useState } from 'react'

import { api, ApiError } from '../../api'
import type { BulkStudentRow, IssuedStudent } from '../../api/types/roster'
import type { AdminTeamRow } from '../../api/types/teams'
import Button from '../../ui/Button'
import Field, { fieldClass } from '../../ui/Field'
import Placard from '../../ui/Placard'
import IssuedPins from './IssuedPins'
import ErrorText from '../../ui/ErrorText'

/**
 * إنشاء الطلاب — إفراديًّا ولصقًا (و-٢١).
 *
 * **الرمز يُولَّد في الخادم ولا يُكتَب هنا**، ولا حقل له في النموذج أصلًا:
 * مشرفٌ يملأ مئتَي رمز بيده سيكتب `1234` للجميع، وهو بعينه ما يُسقط
 * `NFR-03`. ويُعرض **مرّةً واحدة** بعد الإنشاء — لا يُخزَّن نصًّا ولا يعود في
 * أيّ قراءة.
 *
 * **واللصقة ليست ترفًا:** مئتا طالب واحدًا واحدًا شاشةٌ لا تُستعمل، ومن لا
 * يستعملها يؤجّل الإدخال (خ-١). وهي تمرّ بنفس كتابة الإفراديّ في الخدمة، لا
 * بمسارٍ ثانٍ حرٍّ في أن يفترق عنه.
 */

/**
 * سطر = `الاسم, رقم الطالب`. الفاصلة أو التبويب — لأن النسخ من جدول يأتي
 * بالتبويب، ومن محرّر نصّ بالفاصلة؛ وإلزامُ أحدهما يُفشل اللصقة بلا سبب.
 *
 * والسطور الفاسدة **تُترك للخادم** لا تُرشَّح هنا: ترشيحٌ صامتٌ في الواجهة
 * يُنتج لصقةً «نجحت» وفيها طلابٌ لم يُضافوا ولم يُبلَّغ عنهم.
 */
function parseRows(text: string): BulkStudentRow[] {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line)
    .map((line) => {
      const parts = line.split(/[,\t]/).map((part) => part.trim())
      return { full_name: parts[0] ?? '', student_no: parts[1] ?? '' }
    })
}

export default function NewStudentForm({
  teams,
  onCreated,
}: {
  teams: AdminTeamRow[]
  onCreated: () => void
}) {
  const [teamId, setTeamId] = useState('')
  const [fullName, setFullName] = useState('')
  const [studentNo, setStudentNo] = useState('')
  const [paste, setPaste] = useState('')
  const [issued, setIssued] = useState<IssuedStudent[]>([])
  const [failed, setFailed] = useState<string[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const active = teams.filter((t) => !t.archived_at)
  const parsed = parseRows(paste)

  async function run(action: () => Promise<void>) {
    setBusy(true)
    setError('')
    setFailed([])
    try {
      await action()
      onCreated()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  const addOne = () =>
    run(async () => {
      const student = await api.admin.createStudent({
        full_name: fullName.trim(),
        student_no: studentNo.trim(),
        team_id: teamId,
      })
      setIssued([student])
      setFullName('')
      setStudentNo('')
    })

  const addMany = () =>
    run(async () => {
      const result = await api.admin.createStudentsBulk(teamId, parsed)
      setIssued(result.created)
      setFailed(result.failed.map((f) => `السطر ${f.line}: ${f.message}`))
      setPaste('')
    })

  if (issued.length) return <IssuedPins issued={issued} onDone={() => setIssued([])} />

  return (
    <div className="flex flex-col gap-3.5">
      <Placard title="السرب الهدف">
        <Field label="السرب" htmlFor="new_student_team">
          <select
            id="new_student_team"
            value={teamId}
            onChange={(e) => setTeamId(e.target.value)}
            className={fieldClass}
          >
            <option value="">اختر سربًا</option>
            {active.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </Field>
        <p className="text-[12px] text-(--color-text-dim)">
          الرمز يولّده الخادم ويُعرض مرّة واحدة بعد الإضافة — لا يُكتب هنا ولا يُخزَّن نصًّا.
        </p>
      </Placard>

      <Placard title="طالب واحد">
        <Field label="الاسم" htmlFor="new_student_name">
          <input
            id="new_student_name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className={fieldClass}
          />
        </Field>
        <Field label="رقم الطالب — به يدخل" htmlFor="new_student_no">
          <input
            id="new_student_no"
            inputMode="numeric"
            value={studentNo}
            onChange={(e) => setStudentNo(e.target.value)}
            className={fieldClass}
          />
        </Field>
        <Button
          disabled={busy || !teamId || !fullName.trim() || !studentNo.trim()}
          onClick={addOne}
          className="w-full"
        >
          {busy ? 'جارٍ الإضافة…' : 'إضافة طالب'}
        </Button>
      </Placard>

      <Placard title="لصق قائمة" aside={parsed.length ? `${parsed.length} سطرًا` : undefined}>
        <Field label="سطر لكل طالب: الاسم، ثمّ رقم الطالب" htmlFor="new_students_paste">
          <textarea
            id="new_students_paste"
            rows={6}
            value={paste}
            onChange={(e) => setPaste(e.target.value)}
            placeholder={'سالم العتيبي, 1002\nبندر الشمري, 1003'}
            className={`${fieldClass} min-h-[140px] py-2 leading-7`}
          />
        </Field>
        <p className="mb-3 text-[12px] text-(--color-text-dim)">
          السطر الذي يفشل يُبلَّغ عنه وحده، ولا يُسقط بقيّة اللصقة.
        </p>
        <Button disabled={busy || !teamId || !parsed.length} onClick={addMany} className="w-full">
          {busy ? 'جارٍ الإضافة…' : 'إضافة القائمة'}
        </Button>
      </Placard>

      {failed.length ? (
        <Placard title="سطور لم تُضَف" aside={`${failed.length}`}>
          {failed.map((line) => (
            <p key={line} className="mb-1 text-[13px] text-(--color-red-text)">
              {line}
            </p>
          ))}
        </Placard>
      ) : null}

      {error ? <ErrorText spacing="">{error}</ErrorText> : null}
    </div>
  )
}
