import { useState } from 'react'

import { api, ApiError } from '../../api'
import type { FuelWeek } from '../../api/types/fuel'
import Button from '../../ui/Button'
import EmptyState from '../../ui/EmptyState'
import Field, { fieldClass } from '../../ui/Field'
import Placard from '../../ui/Placard'
import ErrorText from '../../ui/ErrorText'

/**
 * «+ إضافة مهمة لهذا الأسبوع» — النموذج المعتمد (و-٢١).
 *
 * **كانت الفجوة واجهةً لا خلفية:** `fuel_week.add_task` مبنيّ ومُختبَر، و
 * `api.admin.addFuelTask` موصولٌ منذ و-٢٠ — ولم يكن له زرٌّ واحد. فالمسار
 * موجودٌ لا يُستدعى، وهو أسوأ من الغائب: يُحسَب مبنيًّا في الجرد.
 *
 * **ولا يُخلَط بـ«نشاط جديد»:** ذاك يُنشئ نشاطًا بتعريفه وبنوده في الجمعية
 * كلّها، وهذا يُسند نشاطًا **قائمًا** إلى أسبوعٍ بعينه. خلطُهما كان يجعل
 * المشرف ينشئ «العشاء» مرّتين ليضيفه إلى أسبوعين.
 *
 * و`available` تصل محسوبةً من الخادم — الفرقُ بين كلّ الأنشطة ومهامِّ الأسبوع
 * قاعدةٌ لا عرض، ولا تُحسَب هنا.
 */

export default function AddWeekTaskForm({
  week,
  onChanged,
}: {
  week: FuelWeek
  onChanged: (next: FuelWeek) => void
}) {
  const [activityId, setActivityId] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit() {
    setBusy(true)
    setError('')
    try {
      onChanged(await api.admin.addFuelTask(activityId, week.week_start))
      setActivityId('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Placard title="إضافة مهمّة لهذا الأسبوع" aside="بعض الأسابيع تختلف مهامّها">
      {week.available.length ? (
        <>
          <Field label="النشاط" htmlFor="week_task_activity">
            <select
              id="week_task_activity"
              value={activityId}
              onChange={(e) => setActivityId(e.target.value)}
              className={fieldClass}
            >
              <option value="">اختر نشاطًا…</option>
              {week.available.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </Field>
          {error ? <ErrorText>{error}</ErrorText> : null}
          <Button disabled={busy || !activityId} onClick={submit} className="w-full">
            {busy ? 'جارٍ الإضافة…' : 'إضافة إلى هذا الأسبوع'}
          </Button>
        </>
      ) : (
        <EmptyState>كل الأنشطة القائمة مهامُّ في هذا الأسبوع — أنشئ نشاطًا جديدًا أدناه.</EmptyState>
      )}
    </Placard>
  )
}
