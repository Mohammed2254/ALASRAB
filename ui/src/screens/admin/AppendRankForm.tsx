import { useState } from 'react'

import { api, ApiError } from '../../api'
import Button from '../../ui/Button'
import Field, { rowInputClass } from '../../ui/Field'
import Placard from '../../ui/Placard'
import ErrorText from '../../ui/ErrorText'


/**
 * «+ إضافة رتبة» — النموذج المعتمد (و-٢١).
 *
 * **في قمّة السُّلّم وحدها، وذلك قرارٌ لا قيد تنفيذ:** `highest_achieved_tier`
 * مِسنَنٌ يحفظ *رقم* الرتبة لا هويّتها، فإدخالُ رتبةٍ في الوسط يُعيد ترقيم ما
 * بعدها — طالبٌ مِسنَنُه ٣ يصير ٣ رتبةً أدنى، **بلا أن ينقص الرقم** فلا
 * يُطلقه مشغّل ث-١٣ب ولا يراه أحد. والخادم هو من يحرس هذا، لا هذه الشاشة.
 *
 * ولا `key` ولا `tier` في النموذج: الأوّل يولّده الخادم، والثاني يحسبه —
 * موضعُ الرتبة في السُّلّم قاعدةٌ لا عرض.
 */
export default function AppendRankForm({ onAppended }: { onAppended: () => void }) {
  const [name, setName] = useState('')
  const [atHours, setAtHours] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit() {
    setBusy(true)
    setError('')
    try {
      await api.admin.appendThreshold(name.trim(), atHours.trim())
      setName('')
      setAtHours('')
      onAppended()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Placard title="إضافة رتبة" aside="في قمّة السُّلّم">
      <Field label="اسم الرتبة" htmlFor="rank_name">
        <input
          id="rank_name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className={`${rowInputClass} w-full`}
        />
      </Field>
      <Field label="عتبة الساعات — يجب أن تتجاوز أعلى رتبة قائمة" htmlFor="rank_hours">
        <input
          id="rank_hours"
          inputMode="decimal"
          value={atHours}
          onChange={(e) => setAtHours(e.target.value)}
          className={`${rowInputClass} w-full`}
        />
      </Field>
      {error ? <ErrorText>{error}</ErrorText> : null}
      <p className="mb-3 text-[12px] text-(--color-text-dim)">
        الرتبة الجديدة تُضاف أعلى السُّلّم، فلا يفقد أحدٌ رتبةً بلغها. وإدخال رتبة بين رتبتين
        قائمتين غير متاح — يُعيد ترقيم ما بعدها.
      </p>
      <Button disabled={busy || !name.trim() || !atHours.trim()} onClick={submit} className="w-full">
        {busy ? 'جارٍ الإضافة…' : 'إضافة رتبة'}
      </Button>
    </Placard>
  )
}
