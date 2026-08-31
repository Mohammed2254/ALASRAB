import { useState } from 'react'

import Placard from '../components/Placard'
import { useApp } from '../state/AppState'

/*
  الدخول: رقم الطالب ورمز من أربعة أرقام.

  لا بريد ولا كلمة مرور تُنسى — والرمز يسلّمه المشرف مع البطاقة. أبسط ما يقبله
  مشرف غير تقني، وأقلّ ما يقف بين الطالب وبطاقته.
*/
export default function Login() {
  const { login } = useApp()
  const [studentNo, setStudentNo] = useState('')
  const [pin, setPin] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await login(studentNo.trim(), pin.trim())
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="taxi-in mx-auto max-w-[420px] px-4 pt-6">
      <h1 className="font-display mb-1 text-[34px] leading-none">الأسراب</h1>
      <p className="mb-5 text-[13px] text-muted">ادخل برقمك ورمزك للوصول إلى بطاقتك.</p>

      <Placard title="تسجيل الدخول">
        <form onSubmit={onSubmit} noValidate>
          <label htmlFor="student_no" className="mb-1.5 block text-[13px]">
            رقم الطالب
          </label>
          <input
            id="student_no"
            inputMode="numeric"
            autoComplete="username"
            value={studentNo}
            onChange={(e) => setStudentNo(e.target.value)}
            className="mb-4 min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
          />

          <label htmlFor="pin" className="mb-1.5 block text-[13px]">
            الرمز (أربعة أرقام)
          </label>
          <input
            id="pin"
            type="password"
            inputMode="numeric"
            maxLength={4}
            autoComplete="current-password"
            value={pin}
            onChange={(e) => setPin(e.target.value)}
            className="min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] tracking-[0.3em] text-paint"
          />

          {error && (
            <p role="alert" className="mt-3 text-[13px] text-hold">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy || !studentNo || pin.length !== 4}
            className="mt-5 min-h-[48px] w-full border border-taxi bg-taxi text-[16px] text-asphalt transition-opacity disabled:opacity-40"
          >
            {busy ? 'جارٍ الدخول…' : 'دخول'}
          </button>
        </form>

        <p className="mt-4 border-t border-concrete/35 pt-3 text-[12px] text-muted">
          نسيت رمزك؟ المشرف يعيد تعيينه لك — لا توجد استعادة ذاتية لأن الحساب بلا
          بريد ولا جوال موثّق.
        </p>
      </Placard>
    </div>
  )
}
