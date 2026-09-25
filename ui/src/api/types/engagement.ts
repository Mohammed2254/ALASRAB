/**
 * عقد التفاعل — `schemas/engagement.py`: سؤال اليوم · الملاحظة المجهولة ·
 * طيار الأسبوع.
 *
 * **ثلاث حالات "فارغة مصمَّمة" (`null` لا `404`)** — نفس نمط `team: null`
 * في `GET /me/deck` منذ و-١٣: لا سؤال اليوم، لم يُجَب بعد، لم يُختَر طيار
 * الأسبوع.
 */
import type { Count, Decimal } from '../brand'

export type Choice = { id: Count; text: string }

export type Answered = {
  choice_id: Count
  correct: boolean
  correct_id: Count
  note: string
  awarded_hours: Decimal
}

export type Question = {
  id: Count
  prompt: string
  choices: Choice[]
  answered: Answered | null
}

export type TodayQuestion = { question: Question | null }

export type WeekPilotRow = { full_name: string; reason: string }

export type WeekPilot = { pilot: WeekPilotRow | null }
