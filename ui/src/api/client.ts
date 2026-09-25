/**
 * نقطة الاتّصال الوحيدة بالخادم — منقولة عن `web/src/lib/api.js` بمنطقها كما
 * هو، ومكتوبة الأنواع.
 *
 * **الكوكي `HttpOnly` يُرسله المتصفّح تلقائيًّا** عبر وكيل Vite (أصل واحد)،
 * فلا توكن يُدار هنا ولا يُخزَّن في `localStorage` — وهو ما يجعل سرقته عبر
 * XSS مستحيلة لا صعبة (ADR-003 · ADR-006).
 *
 * **ورسائل الخطأ تأتي من الخادم حرفيًّا.** نسخُها هنا يُنتج نسختين تتباعدان،
 * وفي شاشة الدخول قد تكشف إحداهما ما تُخفيه الأخرى (تعداد الطلاب).
 */

const BASE = '/api'

export class ApiError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

type Options = { method?: string; body?: unknown }

async function request<T>(path: string, { method = 'GET', body }: Options = {}): Promise<T> {
  const init: RequestInit = { method }
  // `GET` لا يحمل جسمًا: بناؤه شرطيًّا يمنع إرسال `undefined` نصًّا.
  if (body !== undefined) {
    init.headers = { 'Content-Type': 'application/json' }
    init.body = JSON.stringify(body)
  }

  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, init)
  } catch {
    // `status: 0` علامة انقطاع الشبكة — تميّزها `States.Failed` عن خطأ خادم.
    throw new ApiError(0, 'تعذّر الوصول إلى الخادم. تحقّق من اتصالك ثم أعد المحاولة.')
  }

  if (res.status === 204) return null as T

  const data: unknown = await res.json().catch(() => null)
  if (!res.ok) {
    const message =
      (data as { message?: string } | null)?.message ?? 'حدث خطأ غير متوقّع.'
    throw new ApiError(res.status, message)
  }
  return data as T
}

async function requestForm<T>(path: string, formData: FormData): Promise<T> {
  let res: Response
  try {
    // **بلا `Content-Type` عمدًا:** ضبطه هنا يكسر الحدّ الفاصل (boundary) صمتًا،
    // فالمتصفّح وحده يعرف الحدّ الذي ولّده.
    res = await fetch(`${BASE}${path}`, { method: 'POST', body: formData })
  } catch {
    throw new ApiError(0, 'تعذّر الوصول إلى الخادم. تحقّق من اتصالك ثم أعد المحاولة.')
  }
  const data: unknown = await res.json().catch(() => null)
  if (!res.ok) {
    const message = (data as { message?: string } | null)?.message ?? 'حدث خطأ غير متوقّع.'
    throw new ApiError(res.status, message)
  }
  return data as T
}

export { request, requestForm }
