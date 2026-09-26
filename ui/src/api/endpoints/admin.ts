/**
 * كل مسارات المشرف — مُجمَّعة هنا لأن `routes/admin.py` نفسه ملفٌّ خلفيّ
 * واحد رغم تفرّق مخطّطاته بين خمسة ملفّات (`و-١٧.md` §٢ قرار ٣، نفس منطق
 * `me.ts`). تحويلات الشبكة (نصّ نموذج ← رقم سلكيّ) تقع هنا حصرًا — `Number()`
 * ممنوعة في الشاشات (قرار ٥).
 */
import { request } from '../client'
import type { AdminEntryResult, AdminTahdirEntryForm, OrgTahdirReport, QueueItem, ReviewResult } from '../types/adminQueue'
import type { AdminNotesList, ChooseWeekPilotForm, ChosenWeekPilot, MarkedNote } from '../types/engagement'
import type { QuranRoster } from '../types/quranRoster'
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

const thresholdsPayload = (rows: ThresholdRowForm[]) =>
  rows.map((r) => ({ key: r.key, name: r.name, tier: Number(r.tier), at_hours: r.at_hours }))

const weightsPayload = (form: CreateWeightVersionForm) => ({
  effective_from: form.effective_from,
  note: form.note,
  weights: form.weights,
  multipliers: form.multipliers,
})

export const adminApi = {
  report: (days = 7) => request<Report>(`/admin/report?days=${days}`),
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

  notes: () => request<AdminNotesList>('/admin/notes'),
  markNoteRead: (id: number) => request<MarkedNote>(`/admin/notes/${id}`, { method: 'PATCH', body: { read: true } }),

  chooseWeekPilot: (form: ChooseWeekPilotForm) =>
    request<ChosenWeekPilot>('/admin/week/pilot', { method: 'POST', body: form }),
}
