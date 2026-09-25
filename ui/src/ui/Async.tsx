import type { ReactNode } from 'react'

import { ApiError } from '../api/client'
import type { Async as AsyncState } from '../state/useAsync'
import Button from './Button'
import Placard from './Placard'

/**
 * حالات الشاشة الثلاث — TypeScript عن `web/src/components/States.jsx`
 * بمنطقها كما هو. رسالة الخطأ تسمّي المشكلة **والحلّ** معًا.
 */
export function Loading({ title = 'جارٍ التحميل' }: { title?: string | undefined }) {
  return (
    <Placard title={title}>
      <p className="py-2 text-[14px] text-(--color-text-dim)">لحظة…</p>
    </Placard>
  )
}

export function Failed({ error, onRetry }: { error: Error | null; onRetry: () => void }) {
  const offline = error instanceof ApiError && error.status === 0
  return (
    <Placard title="تعذّر العرض">
      <p className="text-[14px] text-(--color-red-text)">{error?.message ?? 'حدث خطأ غير متوقّع.'}</p>
      <p className="mt-2 text-[13px] text-(--color-text-dim)">
        {offline ? 'تحقّق من اتصالك بالشبكة ثم أعد المحاولة.' : 'إن تكرّر هذا فأخبر المشرف بوقت حدوثه.'}
      </p>
      <Button variant="outline" onClick={onRetry} className="mt-3">
        إعادة المحاولة
      </Button>
    </Placard>
  )
}

/** يختصر النمط المتكرّر: تحميل ← خطأ ← بيانات. */
export function Async<T>({
  state,
  children,
  loadingTitle,
}: {
  state: AsyncState<T>
  children: (data: T) => ReactNode
  loadingTitle?: string | undefined
}) {
  if (state.status === 'loading') return <Loading title={loadingTitle} />
  if (state.status === 'error') return <Failed error={state.error} onRetry={state.reload} />
  return children(state.data)
}
