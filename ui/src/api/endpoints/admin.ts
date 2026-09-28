/**
 * كل مسارات المشرف — مُجمَّعة هنا لأن `routes/admin.py` نفسه ملفٌّ خلفيّ
 * واحد رغم تفرّق مخطّطاته بين خمسة ملفّات (`و-١٧.md` §٢ قرار ٣، نفس منطق
 * `me.ts`). تحويلات الشبكة (نصّ نموذج ← رقم سلكيّ) تقع هنا حصرًا — `Number()`
 * ممنوعة في الشاشات (قرار ٥).
 */
import { request, requestForm } from '../client'
import type { AdminEntryResult, AdminTahdirEntryForm, OrgTahdirReport, QueueItem, ReviewResult } from '../types/adminQueue'
import type { AttendanceStatus, RecordedAttendance, UndoneAttendance } from '../types/attendance'
import type { AuditLog } from '../types/audit'
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
import type { AddedQuranEntry, AddQuranEntryForm, QuranEventsList, QuranRoster, ReversedEvent } from '../types/quran'
import type { Report, ResetPinResult } from '../types/report'
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
  tahdirReport: () => request<OrgTahdirReport>('/admin/tahdir/report'),
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

  addFuelTask: (activityId: number, weekStart?: string) =>
    request<FuelWeek>(`/admin/fuel/week/tasks${weekQuery(weekStart)}`, {
      method: 'POST',
      body: { activity_id: activityId },
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

  notes: () => request<AdminNotesList>('/admin/notes'),
  markNoteRead: (id: number) => request<MarkedNote>(`/admin/notes/${id}`, { method: 'PATCH', body: { read: true } }),

  chooseWeekPilot: (form: ChooseWeekPilotForm) =>
    request<ChosenWeekPilot>('/admin/week/pilot', { method: 'POST', body: form }),

  auditLog: () => request<AuditLog>('/admin/audit'),

  fuelActivities: () => request<ActivitiesList>('/admin/fuel/activities'),
  createFuelActivity: (form: CreateActivityForm) =>
    request<CreatedActivity>('/admin/fuel/activities', { method: 'POST', body: form }),
  assessFuel: (form: AssessForm) => request<Assessed>('/admin/fuel/assess', { method: 'POST', body: assessPayload(form) }),

  attendance: () => request<AttendanceStatus>('/admin/attendance'),
  recordAttendance: (absentUserIds: number[]) =>
    request<RecordedAttendance>('/admin/attendance', { method: 'POST', body: { absent_user_ids: absentUserIds } }),
  undoAttendance: () => request<UndoneAttendance>('/admin/attendance/undo', { method: 'POST' }),

  quranEvents: (userId: string) => request<QuranEventsList>(`/admin/quran/events?user_id=${Number(userId)}`),
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
