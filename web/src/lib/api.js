/*
  عميل الـAPI — الحدّ الوحيد بين الواجهة والخادم.

  **لا يحسب شيئًا.** كل رقم يأتي محسوبًا من الخادم: رتبةً ورصيدًا ونسبةً وحالة
  طيران. وهذا ليس تفضيلًا أسلوبيًّا: حساب الرتبة في مكانين يعني أنهما سيتباعدان،
  فيرى الطالب رقمًا في بطاقته وآخر في لوحة الصدارة (`AGENTS.md` ٥).

  الكوكي `HttpOnly` يُرسله المتصفّح تلقائيًّا عبر وكيل Vite (أصل واحد)، فلا توكن
  يُدار هنا ولا يُخزَّن في `localStorage` حيث يقرؤه أي سكربت.
*/

const BASE = '/api'

/** خطأ يحمل رمز الحالة، فتفرّق الواجهة بين «لست داخلًا» و«عطل» و«انقطاع». */
export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

async function request(path, { method = 'GET', body } = {}) {
  // الجسم يُبنى شرطيًّا لا يُمرَّر `undefined`: `GET` بجسمٍ غير صالح، وبناؤه
  // هكذا يجعل النيّة صريحة للقارئ وللأداة معًا.
  const init = { method }
  if (body !== undefined) {
    init.headers = { 'Content-Type': 'application/json' }
    init.body = JSON.stringify(body)
  }

  let res
  try {
    res = await fetch(`${BASE}${path}`, init)
  } catch {
    // انقطاع الشبكة لا يعطي استجابة أصلًا، فرسالته تُصاغ هنا.
    throw new ApiError(0, 'تعذّر الوصول إلى الخادم. تحقّق من اتصالك ثم أعد المحاولة.')
  }

  if (res.status === 204) return null

  const data = await res.json().catch(() => null)
  if (!res.ok) {
    // الرسالة من الخادم كما هي: هو من يقرّر ما يُقال للمستخدم، وصياغتها هنا
    // تعني نسختين تتباعدان — وفي الدخول تحديدًا تكشف نسخةٌ ما تخفيه الأخرى.
    throw new ApiError(res.status, data?.message ?? 'حدث خطأ غير متوقّع.')
  }
  return data
}

export const api = {
  /*
    **بلا `org_id`.** العقد لا يحمله (`API.md` §٣): مراهقٌ لا يكتب رقم منظمة،
    والعميل لا يجوز أن يستكشف المنظمات. الخادم يحلّه.
  */
  login: (studentNo, pin) =>
    request('/auth/login', { method: 'POST', body: { student_no: studentNo, pin } }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  me: () => request('/auth/me'),

  deck: () => request('/me/deck'),

  myEvents: (limit = 20) => request(`/me/events?limit=${limit}`),

  myReadings: () => request('/me/readings'),
  submitReading: (body) => request('/me/readings', { method: 'POST', body }),

  readingQueue: () => request('/admin/readings'),
  approveReadings: (ids) =>
    request('/admin/readings/approve', { method: 'POST', body: { ids } }),
  rejectReading: (id, reason) =>
    request(`/admin/readings/${id}/reject`, { method: 'POST', body: { reason } }),
}
