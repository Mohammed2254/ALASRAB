/** سؤال اليوم · الملاحظة المجهولة · طيار الأسبوع — `schemas/engagement.py`. */
import { request } from '../client'
import type { Answered, TodayQuestion, WeekPilot } from '../types/engagement'

export const engagementApi = {
  todayQuestion: () => request<TodayQuestion>('/questions/today'),
  answerQuestion: (questionId: number, choiceId: number) =>
    request<Answered>(`/questions/${questionId}/answer`, { method: 'POST', body: { choice_id: choiceId } }),
  // ٢٠١ بلا جسمٍ إطلاقًا (`API.md`) — `client.ts::request` يُرجع `null` على
  // جسمٍ فارغ فعلًا، فلا حاجة لغلافٍ خاصّ هنا.
  submitNote: (body: string) => request<null>('/notes', { method: 'POST', body: { body } }),
  weekPilot: () => request<WeekPilot>('/week/pilot'),
}
