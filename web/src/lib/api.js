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

/**
 * كـ`request` — لكن `multipart/form-data` لملفّ حقيقيّ (و-٥). لا
 * `Content-Type` يُضبَط يدويًّا: المتصفّح يبنيه بحدٍّ فاصل صحيح تلقائيًّا
 * حين يُمرَّر `FormData` مباشرةً — ضبطه هنا يكسر الحدّ الفاصل صمتًا.
 */
async function requestForm(path, formData) {
  let res
  try {
    res = await fetch(`${BASE}${path}`, { method: 'POST', body: formData })
  } catch {
    throw new ApiError(0, 'تعذّر الوصول إلى الخادم. تحقّق من اتصالك ثم أعد المحاولة.')
  }
  const data = await res.json().catch(() => null)
  if (!res.ok) {
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

  report: (days = 7) => request(`/admin/report?days=${days}`),
  resetPin: (userId) => request(`/admin/users/${userId}/reset-pin`, { method: 'POST' }),
  readingQueue: () => request('/admin/readings'),
  approveReadings: (ids) =>
    request('/admin/readings/approve', { method: 'POST', body: { ids } }),
  rejectReading: (id, reason) =>
    request(`/admin/readings/${id}/reject`, { method: 'POST', body: { reason } }),

  // و-٧
  weights: () => request('/admin/weights'),
  createWeightVersion: (body) => request('/admin/weights', { method: 'POST', body }),

  thresholds: () => request('/admin/thresholds'),
  saveThresholds: (thresholds) =>
    request('/admin/thresholds', { method: 'POST', body: { thresholds } }),
  previewThresholds: (thresholds) =>
    request('/admin/thresholds/preview', { method: 'POST', body: { thresholds } }),

  teams: () => request('/admin/teams'),
  createTeam: (body) => request('/admin/teams', { method: 'POST', body }),
  archiveTeam: (id) => request(`/admin/teams/${id}`, { method: 'PATCH', body: { archived: true } }),
  transferMember: (teamId, userId) =>
    request(`/admin/teams/${teamId}/members`, { method: 'POST', body: { user_id: userId } }),

  auditLog: () => request('/admin/audit'),

  // و-٨
  fuelActivities: () => request('/admin/fuel/activities'),
  createFuelActivity: (body) => request('/admin/fuel/activities', { method: 'POST', body }),
  assessFuel: (body) => request('/admin/fuel/assess', { method: 'POST', body }),
  station: () => request('/station'),

  // و-٩ب
  pilotsBoard: () => request('/boards/pilots'),
  teamsBoard: () => request('/boards/teams'),
  formation: (scope = 'team') => request(`/boards/formation?scope=${scope}`),

  // و-٩ج
  todayQuestion: () => request('/questions/today'),
  answerQuestion: (id, choiceId) =>
    request(`/questions/${id}/answer`, { method: 'POST', body: { choice_id: choiceId } }),

  // و-٩د
  submitNote: (body) => request('/notes', { method: 'POST', body: { body } }),
  weekPilot: () => request('/week/pilot'),
  chooseWeekPilot: (userId, reason) =>
    request('/admin/week/pilot', { method: 'POST', body: { user_id: userId, reason } }),
  adminNotes: () => request('/admin/notes'),
  markNoteRead: (id) => request(`/admin/notes/${id}`, { method: 'PATCH', body: { read: true } }),

  // و-٩هـ
  attendance: () => request('/admin/attendance'),
  recordAttendance: (absentUserIds) =>
    request('/admin/attendance', { method: 'POST', body: { absent_user_ids: absentUserIds } }),
  undoAttendance: () => request('/admin/attendance/undo', { method: 'POST' }),

  // و-٦
  quranStudents: () => request('/admin/quran/students'),
  quranEvents: (userId) => request(`/admin/quran/events?user_id=${userId}`),
  quranEntry: (body) => request('/admin/quran/entry', { method: 'POST', body }),
  reverseEvent: (eventId, reason) =>
    request(`/admin/events/${eventId}/reverse`, { method: 'POST', body: { reason } }),

  // و-١١ — تحضير القراءة
  myTahdir: () => request('/me/tahdir'),
  submitTahdir: (body) => request('/me/tahdir', { method: 'POST', body }),
  tahdirQueue: () => request('/admin/tahdir'),
  // اعتماد/رفض تحضير: نفس مساري القراءة العامّة القائمين حرفيًّا — عامّان
  // على معرّف الطلب بصرف النظر عن نوعه.
  adminTahdirEntry: (body) => request('/admin/tahdir/entry', { method: 'POST', body }),
  tahdirReport: () => request('/admin/tahdir/report'),

  // و-٥ — استيراد راصد. الاسم تاريخيّ (`/admin/paste/*`) — الوظيفة استيراد
  // ملفّ لا لصق نصّ (`docs/slices/و-٥.md` §٢ قرار #١٠).
  pastePreview: (file, occurredOn) => {
    const form = new FormData()
    form.set('file', file)
    form.set('occurred_on', occurredOn)
    return requestForm('/admin/paste/preview', form)
  },
  pasteCommit: (file, occurredOn, nameResolutions) => {
    const form = new FormData()
    form.set('file', file)
    form.set('occurred_on', occurredOn)
    if (nameResolutions && Object.keys(nameResolutions).length) {
      form.set('name_resolutions', JSON.stringify(nameResolutions))
    }
    return requestForm('/admin/paste/commit', form)
  },
}
