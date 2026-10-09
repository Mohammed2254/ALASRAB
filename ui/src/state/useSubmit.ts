/**
 * كتابةٌ بحالتين صريحتين — **شقيقُ `useAsync` لا بديلٌ عنه.**
 *
 * `useAsync` يملك القراءة (`loading` · `ready` · `error`)، ولم يكن للكتابة
 * نظير — فتكفّلت بها كلُّ شاشةٍ بيدها. والقياس: ثلاثون شاشةً تحمل
 * `const [busy, setBusy]` وثلاثون `const [error, setError]`، **والسطرُ**
 * `setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')`
 * **مكرَّرٌ إحدى وثلاثين مرّة** في ستٍّ وعشرين ملفًّا.
 *
 * **وفيها نمطان لا واحد** — وهذا ما كان سيُكسَر لو وُحِّدت بسهولة:
 *
 * · **ثمانٍ وعشرون** تُحرّر `busy` في `finally` — نموذجٌ يبقى معروضًا بعد
 *   النجاح، فالزرّ يعود قابلًا للنقر.
 * · **وثلاثٌ تُحرّره داخل `catch` وحده عن قصد** (`DailyQuestion` ·
 *   `Attendance` إرسالًا وتراجعًا): نجاحُها ينادي `onAnswered`/`onRecorded`
 *   فيُفكَّك المكوّن أو يُعاد تحميله، **فبقاءُ `busy` هو ما يمنع إرسالًا
 *   مزدوجًا أثناء الانتقال**. و`finally` فيها يُعيد تمكين الزرّ لحظةً —
 *   انحدارٌ صامت.
 *
 * (ظننتُ أوّلًا أن الثلاثَ عطلٌ ونسيانُ `finally`. قراءتُها أثبتت العكس،
 * فصار الخيار معاملًا معلَنًا لا افتراضًا واحدًا يُفرَض على نمطين.)
 *
 * **والرسالةُ من الخادم لا من هنا:** `ApiError.message` هو ما كتبته الخدمة
 * بالعربية (نمط `abort(exc.status, message=str(exc))`)، والنصُّ العامّ
 * احتياطٌ لانقطاع الشبكة وحده — لا بديلٌ عن رسالةٍ وصلت.
 */
import { useCallback, useState } from 'react'

import { ApiError } from '../api'

const FALLBACK = 'حدث خطأ غير متوقّع.'

export type Submit = {
  /** يُعطَّل بها الزرّ أثناء الطلب — فلا إرسالٌ مزدوج بنقرتين. */
  busy: boolean
  /** رسالةُ آخر فشل، أو `''`. تُمرَّر إلى `ui/ErrorText`. */
  error: string
  /**
   * يُشغّل العمل ويُرجع `true` عند النجاح — فالمستدعي يقرّر ما بعده
   * (تصفيرُ نموذج · إعادةُ تحميل · إغلاق) بلا أن يفحص الحالة مرّةً أخرى.
   *
   * و`keepBusyOnSuccess` للشاشات التي يُفكَّك مكوّنُها عند النجاح: يبقى
   * الزرّ معطَّلًا فلا يُنقَر مرّتين أثناء الانتقال.
   */
  run: (
    action: () => Promise<void>,
    options?: { keepBusyOnSuccess?: true },
  ) => Promise<boolean>
  /** لإخفاء خطأٍ سابق عند تغيير المُدخَلات. */
  clear: () => void
}

export function useSubmit(): Submit {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const run = useCallback(
    async (action: () => Promise<void>, options?: { keepBusyOnSuccess?: true }) => {
      setBusy(true)
      setError('')
      try {
        await action()
        // التحريرُ عند النجاح **افتراضٌ لا قاعدة**: ثمانٍ وعشرون شاشةً تريده،
        // وثلاثٌ تريد بقاءه لأن مكوّنها يُفكَّك بعد النجاح.
        if (!options?.keepBusyOnSuccess) setBusy(false)
        return true
      } catch (err) {
        setError(err instanceof ApiError ? err.message : FALLBACK)
        // والفشلُ يُحرّر دائمًا — وإلّا عَلِق الزرّ إلى أن تُعاد الصفحة.
        setBusy(false)
        return false
      }
    },
    [],
  )

  const clear = useCallback(() => setError(''), [])

  return { busy, error, run, clear }
}
