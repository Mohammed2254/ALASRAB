/**
 * كل مسارات المشرف — مُجمَّعة هنا لأن `routes/admin.py` نفسه ملفٌّ خلفيّ
 * واحد رغم تفرّق مخطّطاته بين خمسة ملفّات (`و-١٧.md` §٢ قرار ٣، نفس منطق
 * `me.ts`). تحويلات الشبكة (نصّ نموذج ← رقم سلكيّ) تقع هنا حصرًا — `Number()`
 * ممنوعة في الشاشات (قرار ٥).
 */
import { request, requestForm } from '../client'
import type { AdminEntryResult, AdminTahdirEntryForm, OrgTahdirReport, QueueItem, ReviewResult } from '../types/adminQueue'
import type {
  AttendanceStatus,
  RasdLatestImport,
  RecordedAttendance,
  UndoneAttendance,
} from '../types/attendance'
import type { AuditLog } from '../types/audit'
import type { QuestionForm, QuestionRef, QuestionsList } from '../types/dailyQuestion'
import type { AdminDashboard } from '../types/dashboard'
import type { AdminNotesList, ChooseWeekPilotForm, ChosenWeekPilot, MarkedNote } from '../types/engagement'
import type {
  ActivitiesList,
  AssessForm,
  Assessed,
  CreateActivityForm,
  CreatedActivity,
  FuelWeek,
  ScoreRowForm,
} from '../types/fuel'
import type { PasteCommitResult, PastePreview } from '../types/paste'
import type { AddedQuranEntry, AddQuranEntryForm, AmendedEvent, AmendEventForm, QuranEventsList, QuranRoster, ReversedEvent } from '../types/quran'
import type { Report, ResetPinResult } from '../types/report'
import type {
  ActiveSet,
  BulkCreated,
  BulkStudentRow,
  CreateStudentForm,
  IssuedStudent,
  RoleSet,
  RosterList,
} from '../types/roster'
import type {
  CreateWeightVersionForm,
  SaveThresholdsForm,
  ThresholdRowForm,
  Thresholds,
  ThresholdsPreview,
  WeightVersionRef,
  Weights,
} from '../types/rulesAdmin'
import type { ArchivedTeam, CreatedTeam, CreateTeamForm, Teams, TransferredMember } from '../types/teams'

const weekQuery = (weekStart?: string) =>
  weekStart ? `?week_start=${weekStart}` : ''

/**
 * جسم السؤال. **يُرشَّح الخيارات الفارغة هنا لا في الشاشة**: النموذج يعرض
 * أربع خانات ثابتة (فلا حساب فهارس في الواجهة)، والمشرف يملأ اثنتين أو
 * أربعًا — والفارغة ليست خيارًا.
 *
 * و`day` يُحذَف في التعديل: نقلُ سؤالٍ إلى يومٍ آخر مساوٍ لحذفه وإنشائه،
 * والخادم لا يقبله أصلًا (`UpdateQuestionSchema` بلا `day`).
 */
const questionPayload = (form: QuestionForm, withDay: boolean) => ({
  ...(withDay ? { day: form.day } : {}),
  prompt: form.prompt,
  choices: form.choices
    .filter((c) => c.text.trim())
    .map((c) => ({ id: c.id, text: c.text.trim() })),
  correct_id: Number(form.correct_id),
  note: form.note,
  reward_hours: form.reward_hours,
})

const thresholdsPayload = (rows: ThresholdRowForm[]) =>
  rows.map((r) => ({ key: r.key, name: r.name, tier: Number(r.tier), at_hours: r.at_hours }))

const weightsPayload = (form: CreateWeightVersionForm) => ({
  effective_from: form.effective_from,
  note: form.note,
  weights: form.weights,
  multipliers: form.multipliers,
})

const assessPayload = (form: AssessForm) => ({
  team_id: Number(form.team_id),
  activity_id: Number(form.activity_id),
  occurred_on: form.occurred_on,
  scores: form.scores,
})

export const adminApi = {
  report: (days = 7) => request<Report>(`/admin/report?days=${days}`),

  /**
   * لوحة القيادة — **خمسة نداءات متوازية في `Promise.all` لا سلسلة انتظار.**
   *
   * ورفضتُ `allSettled` عمدًا: يدفع خمس فحوص حالة وخمس صور خطأ إلى الشاشة،
   * وهي خمسة GET رخيصة على خادمٍ واحد — إن فشل أحدها فالمشرف يحتاج أن يرى
   * فشلًا، لا لوحةً ينقصها رقمٌ بهدوء.
   *
   * والأعداد تُحسب هنا لا في الشاشة («الواجهة تعرض ولا تحسب»، `AGENTS.md` ٥).
   */
  dashboard: (): Promise<AdminDashboard> =>
    Promise.all([
      request<Report>('/admin/report?days=7'),
      request<{ submissions: QueueItem[] }>('/admin/readings'),
      request<{ submissions: QueueItem[] }>('/admin/tahdir'),
      request<AdminNotesList>('/admin/notes'),
      request<AuditLog>('/admin/audit'),
    ]).then(([report, readings, tahdir, notes, audit]) => ({
      window: report.window,
      totals: report.totals,
      teams_count: report.teams.length,
      pending: {
        readings: readings.submissions.length,
        tahdir: tahdir.submissions.length,
        notes: notes.notes.filter((n) => n.read_at === null).length,
      },
      activity: audit.entries,
    })),
  resetPin: (userId: number) => request<ResetPinResult>(`/admin/users/${userId}/reset-pin`, { method: 'POST' }),

  readingQueue: () => request<{ submissions: QueueItem[] }>('/admin/readings'),
  approveReadings: (ids: number[]) =>
    request<{ results: ReviewResult[] }>('/admin/readings/approve', { method: 'POST', body: { ids } }),
  rejectReading: (id: number, reason: string) =>
    request<{ results: ReviewResult[] }>(`/admin/readings/${id}/reject`, { method: 'POST', body: { reason } }),

  tahdirQueue: () => request<{ submissions: QueueItem[] }>('/admin/tahdir'),
  adminTahdirEntry: (form: AdminTahdirEntryForm) =>
    request<AdminEntryResult>('/admin/tahdir/entry', {
      method: 'POST',
      body: { ...form, user_id: Number(form.user_id), pages: Number(form.pages) },
    }),
  // بلا فترة ⇒ أسبوع اليوم. والخادم يرفض فترةً بطرفٍ واحد أو مقلوبة.
  tahdirReport: (from?: string, to?: string) =>
    request<OrgTahdirReport>(
      from && to ? `/admin/tahdir/report?from=${from}&to=${to}` : '/admin/tahdir/report'
    ),
  quranStudents: () => request<QuranRoster>('/admin/quran/students'),

  teams: () => request<Teams>('/admin/teams'),
  createTeam: (form: CreateTeamForm) => request<CreatedTeam>('/admin/teams', { method: 'POST', body: form }),
  archiveTeam: (teamId: number) =>
    request<ArchivedTeam>(`/admin/teams/${teamId}`, { method: 'PATCH', body: { archived: true } }),
  transferMember: (teamId: string, userId: string) =>
    request<TransferredMember>(`/admin/teams/${Number(teamId)}/members`, {
      method: 'POST',
      body: { user_id: Number(userId) },
    }),

  weights: () => request<Weights>('/admin/weights'),
  createWeightVersion: (form: CreateWeightVersionForm) =>
    request<WeightVersionRef>('/admin/weights', { method: 'POST', body: weightsPayload(form) }),

  thresholds: () => request<Thresholds>('/admin/thresholds'),
  saveThresholds: (form: SaveThresholdsForm) =>
    request<ThresholdsPreview>('/admin/thresholds', {
      method: 'POST',
      body: { thresholds: thresholdsPayload(form.thresholds) },
    }),
  // رتبةٌ جديدة **في قمّة السُّلّم** — بلا `key` وبلا `tier`: الخادم يولّد
  // الأوّل ويحسب الثاني. موضعُ الرتبة قاعدةٌ لا عرض، فلا تحسبه الواجهة.
  appendThreshold: (name: string, atHours: string) =>
    request<ThresholdsPreview>('/admin/thresholds/append', {
      method: 'POST',
      body: { name, at_hours: atHours },
    }),

  previewThresholds: (form: SaveThresholdsForm) =>
    request<ThresholdsPreview>('/admin/thresholds/preview', {
      method: 'POST',
      body: { thresholds: thresholdsPayload(form.thresholds) },
    }),

  // ═══ أسبوع الوقود — و-٢٠ ═══
  //
  // `week_start` اختياريّ: بدونه أسبوع اليوم. والخادم **يُطبّعه** إلى بداية
  // الأسبوع، فلا تُرسل الواجهة تاريخًا «صحيحًا» بحسابها هي.
  fuelWeek: (weekStart?: string) =>
    request<FuelWeek>(`/admin/fuel/week${weekQuery(weekStart)}`),

  // `teamId` نصٌّ خام من `<select>` — التحويل هنا لا في الشاشة (قرار و-١٧ ٥:
  // `Number()` ممنوعة في `src/screens`، تحرسها بوابة AST).
  assignFuelTeam: (activityId: number, teamId: string, weekStart?: string) =>
    request<FuelWeek>(`/admin/fuel/week/team${weekQuery(weekStart)}`, {
      method: 'POST',
      body: { activity_id: activityId, team_id: teamId ? Number(teamId) : null },
    }),

  // `activityId` نصٌّ خام من `<select>` كـ`assignFuelTeam` — التحويل هنا لا
  // في الشاشة (قرار و-١٧ ٥: `Number()` ممنوعة في `src/screens`).
  // و`removeFuelTask` أدناه يأخذ رقمًا لأن مصدره `task.activity_id` لا حقلَ
  // إدخال — فالنوعان مختلفان بسبب لا بسهو.
  addFuelTask: (activityId: string, weekStart?: string) =>
    request<FuelWeek>(`/admin/fuel/week/tasks${weekQuery(weekStart)}`, {
      method: 'POST',
      body: { activity_id: Number(activityId) },
    }),

  removeFuelTask: (activityId: number, weekStart?: string) =>
    request<FuelWeek>(`/admin/fuel/week/tasks${weekQuery(weekStart)}`, {
      method: 'DELETE',
      body: { activity_id: activityId },
    }),

  saveFuelScores: (activityId: number, scores: ScoreRowForm[], weekStart?: string) =>
    request<FuelWeek>(`/admin/fuel/week/scores${weekQuery(weekStart)}`, {
      method: 'POST',
      body: {
        activity_id: activityId,
        scores: scores.map((s) => ({ criterion_id: s.criterion_id, score_pct: s.score_pct })),
      },
    }),

  approveFuelWeek: (weekStart?: string) =>
    request<FuelWeek>(`/admin/fuel/week/approve${weekQuery(weekStart)}`, { method: 'POST' }),

  // ═══ سجلّ الطلاب — و-٢١ ═══
  //
  // `teamId` نصٌّ خام من `<select>`، و`Number()` ممنوعة في `src/screens`
  // (بوابة AST) — فالتحويل هنا كما في `assignFuelTeam`.
  roster: () => request<RosterList>('/admin/users'),

  createStudent: (form: CreateStudentForm) =>
    request<IssuedStudent>('/admin/users', {
      method: 'POST',
      body: {
        full_name: form.full_name,
        student_no: form.student_no,
        team_id: Number(form.team_id),
      },
    }),

  createStudentsBulk: (teamId: string, rows: BulkStudentRow[]) =>
    request<BulkCreated>('/admin/users/bulk', {
      method: 'POST',
      body: { team_id: Number(teamId), rows },
    }),

  setStudentRole: (userId: number, role: string) =>
    request<RoleSet>(`/admin/users/${userId}/role`, { method: 'PATCH', body: { role } }),

  setStudentActive: (userId: number, active: boolean) =>
    request<ActiveSet>(`/admin/users/${userId}/active`, { method: 'PATCH', body: { active } }),

  // ═══ سؤال اليوم — و-٢١ ═══
  //
  // `correct_id` و`id` الخيارات نصوصٌ خام من النموذج، والتحويل هنا لا في
  // الشاشة (قرار و-١٧ ٥: `Number()` ممنوعة في `src/screens`).
  questions: () => request<QuestionsList>('/admin/questions'),

  createQuestion: (form: QuestionForm) =>
    request<QuestionRef>('/admin/questions', { method: 'POST', body: questionPayload(form, true) }),

  updateQuestion: (id: number, form: QuestionForm) =>
    request<QuestionRef>(`/admin/questions/${id}`, {
      method: 'PATCH',
      body: questionPayload(form, false),
    }),

  deleteQuestion: (id: number) =>
    request<void>(`/admin/questions/${id}`, { method: 'DELETE' }),

  notes: () => request<AdminNotesList>('/admin/notes'),
  markNoteRead: (id: number) => request<MarkedNote>(`/admin/notes/${id}`, { method: 'PATCH', body: { read: true } }),

  // `bonus_hours` نصُّ نموذج ⇒ عشريٌّ سلكيّ. التحويل هنا لا في الشاشة.
  chooseWeekPilot: (form: ChooseWeekPilotForm) =>
    request<ChosenWeekPilot>('/admin/week/pilot', {
      method: 'POST',
      body: {
        user_id: form.user_id,
        reason: form.reason,
        bonus_hours: form.bonus_hours.trim() || '0',
      },
    }),

  auditLog: () => request<AuditLog>('/admin/audit'),

  fuelActivities: () => request<ActivitiesList>('/admin/fuel/activities'),
  createFuelActivity: (form: CreateActivityForm) =>
    request<CreatedActivity>('/admin/fuel/activities', { method: 'POST', body: form }),
  assessFuel: (form: AssessForm) => request<Assessed>('/admin/fuel/assess', { method: 'POST', body: assessPayload(form) }),

  attendance: () => request<AttendanceStatus>('/admin/attendance'),
  // الحضور من راصد — للعرض فقط، والإدخال اليدويّ أعلاه احتياطيٌّ موثَّق.
  attendanceFromRasd: () => request<RasdLatestImport>('/admin/attendance/rasd'),
  recordAttendance: (absentUserIds: number[]) =>
    request<RecordedAttendance>('/admin/attendance', { method: 'POST', body: { absent_user_ids: absentUserIds } }),
  undoAttendance: () => request<UndoneAttendance>('/admin/attendance/undo', { method: 'POST' }),

  quranEvents: (userId: string) => request<QuranEventsList>(`/admin/quran/events?user_id=${Number(userId)}`),
  // `quantity` نصُّ نموذج ⇒ عشريٌّ سلكيّ، و`mastery` الفارغ يصير عدمًا —
  // التحويل هنا لا في الشاشة.
  amendEvent: (eventId: number, form: AmendEventForm) =>
    request<AmendedEvent>(`/admin/events/${eventId}/amend`, {
      method: 'POST',
      body: {
        occurred_on: form.occurred_on,
        activity_type: form.activity_type,
        quantity: form.quantity,
        mastery: form.mastery.trim() || null,
        reason: form.reason,
      },
    }),

  reverseEvent: (eventId: number, reason: string) =>
    request<ReversedEvent>(`/admin/events/${eventId}/reverse`, { method: 'POST', body: { reason } }),
  quranEntry: (form: AddQuranEntryForm) =>
    request<AddedQuranEntry>('/admin/quran/entry', {
      method: 'POST',
      body: {
        user_id: Number(form.user_id),
        occurred_on: form.occurred_on,
        activity_type: form.activity_type,
        quantity: form.quantity,
        mastery: form.mastery,
        reason: form.reason,
      },
    }),

  // `multipart/form-data` لا JSON — الملفّ لا يلائم `request()` (قرار ٥،
  // `و-١٨.md §١.١`). أوّل استهلاكٍ حيّ لـ`requestForm` منذ بنائها في و-١٣.
  pastePreview: (file: File, occurredOn: string) => {
    const form = new FormData()
    form.set('file', file)
    form.set('occurred_on', occurredOn)
    return requestForm<PastePreview>('/admin/paste/preview', form)
  },
  pasteCommit: (file: File, occurredOn: string, nameResolutions: Record<string, string>) => {
    const form = new FormData()
    form.set('file', file)
    form.set('occurred_on', occurredOn)
    const entries = Object.entries(nameResolutions)
    if (entries.length) {
      const numeric = Object.fromEntries(entries.map(([name, userId]) => [name, Number(userId)]))
      form.set('name_resolutions', JSON.stringify(numeric))
    }
    return requestForm<PasteCommitResult>('/admin/paste/commit', form)
  },
}
