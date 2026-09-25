/**
 * الدخول — رقم الطالب ورمز من أربعة أرقام.
 *
 * لا بريد ولا كلمة مرور تُنسى: الرمز يسلّمه المشرف مع البطاقة. أبسط ما يقبله
 * مشرفٌ غير تقنيّ، وأقلّ ما يقف بين الطالب وبطاقته.
 *
 * **وهي الشاشة السادسة والعشرون** — النموذج المعتمد لم يحملها (بدأ من داخل
 * التطبيق)، فبُنيت هنا من الرموز وحدها.
 *
 * ومعرّفا الحقلين `student_no` و`pin` **جزءٌ من عقد القياس البصريّ** لا تفصيل:
 * يملأهما `visual-qa.mjs` في كل تشغيلة.
 */
import { useState, type FormEvent } from 'react'

import HexIcon from '../ui/HexIcon'
import { useApp } from '../state/AppState'

const CHEVRON = 'M17 40 L32 22 L47 40'

export default function Login() {
  const { login } = useApp()
  const [studentNo, setStudentNo] = useState('')
  const [pin, setPin] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await login(studentNo.trim(), pin.trim())
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  // `pin.length !== 4` مساواةٌ لا مقارنة — والمقارنات ممنوعة في هذه الطبقة.
  const incomplete = !studentNo || pin.length !== 4

  return (
    <main className="mx-auto w-full max-w-[420px] px-5 pt-10 pb-12">
      <header className="mb-8 flex items-center gap-3">
        <HexIcon size={46} glyph={CHEVRON} />
        <div>
          <h1 className="font-display text-[26px] leading-none font-extrabold">الأسراب</h1>
          <p className="mt-1.5 text-[12px] text-(--color-text-dim)">
            منصّة حفظ القرآن التنافسية
          </p>
        </div>
      </header>

      <section className="rounded-(--radius-lg) border border-(--color-border) bg-(--color-surface) p-5">
        <h2 className="mb-4 font-display text-[14px] font-bold">تسجيل الدخول</h2>

        <form onSubmit={onSubmit} noValidate>
          <label htmlFor="student_no" className="mb-2 block text-[13px] text-(--color-text-dim)">
            رقم الطالب
          </label>
          <input
            id="student_no"
            inputMode="numeric"
            autoComplete="username"
            value={studentNo}
            onChange={(e) => setStudentNo(e.target.value)}
            className="mb-4 min-h-[48px] w-full rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) px-3 text-[16px] text-(--color-text)"
          />

          <label htmlFor="pin" className="mb-2 block text-[13px] text-(--color-text-dim)">
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
            className="min-h-[48px] w-full rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) px-3 text-[16px] text-(--color-text)"
          />

          {error ? (
            <p role="alert" className="mt-3 text-[13px] text-(--color-red-text)">
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={busy || incomplete}
            className="mt-6 min-h-[48px] w-full rounded-(--radius-sm) bg-(--color-accent) text-[16px] font-bold text-(--color-on-accent) disabled:opacity-40"
          >
            {busy ? 'جارٍ الدخول…' : 'دخول'}
          </button>
        </form>

        <p className="mt-5 border-t border-(--color-border) pt-4 text-[12px] text-(--color-text-dim)">
          نسيت رمزك؟ المشرف يعيد تعيينه لك — لا توجد استعادة ذاتية لأن الحساب بلا
          بريد ولا جوّال موثّق.
        </p>
      </section>
    </main>
  )
}
