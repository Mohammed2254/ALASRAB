import Placard from './Placard'

/*
  حالات الشاشة الثلاث، مصمَّمة لا مرتجَلة.

  رسالة الخطأ تسمّي المشكلة **والحلّ** معًا: «تعذّر الجلب» وحدها تترك المستخدم
  واقفًا، ولا يعرف أينتظر أم يعيد المحاولة أم يراجع أحدًا.
*/

export function Loading({ title = 'جارٍ التحميل' }) {
  return (
    <Placard title={title}>
      <p className="py-2 text-[14px] text-muted">لحظة…</p>
    </Placard>
  )
}

export function Failed({ error, onRetry }) {
  const offline = error?.status === 0
  return (
    <Placard title="تعذّر العرض">
      <p className="text-[14px] text-hold">{error?.message ?? 'حدث خطأ غير متوقّع.'}</p>
      <p className="mt-2 text-[13px] text-muted">
        {offline
          ? 'تحقّق من اتصالك بالشبكة ثم أعد المحاولة.'
          : 'إن تكرّر هذا فأخبر المشرف بوقت حدوثه.'}
      </p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 min-h-[44px] border border-taxi px-5 text-[14px] text-taxi"
        >
          إعادة المحاولة
        </button>
      )}
    </Placard>
  )
}

export function Empty({ title, children }) {
  return (
    <Placard title={title}>
      <p className="py-2 text-[14px] text-muted">{children}</p>
    </Placard>
  )
}

/** يختصر النمط المتكرّر: تحميل ← خطأ ← بيانات. */
export function Async({ state, children, loadingTitle }) {
  if (state.status === 'loading') return <Loading title={loadingTitle} />
  if (state.status === 'error') return <Failed error={state.error} onRetry={state.reload} />
  return children(state.data)
}
