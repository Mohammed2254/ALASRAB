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
  /** أيّامٌ متتالية من الإجابات الصحيحة — **مشتقّةٌ في الخادم** لا محسوبة هنا. */
  streak: Count
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

// ═══ الشقّ الإداريّ — الملاحظات · اختيار طيار الأسبوع ═══

export type AdminNoteRow = { id: Count; body: string; day: string; read_at: string | null }
export type AdminNotesList = { notes: AdminNoteRow[] }
export type MarkedNote = { id: Count; read_at: string }

/** `bonus_hours` نصُّ إدخال — يتحوّل عند حدّ الشبكة لا في الشاشة. */
export type ChooseWeekPilotForm = { user_id: Count; reason: string; bonus_hours: string }
export type ChosenWeekPilot = {
  user_id: Count
  full_name: string
  week_start: string
  bonus_hours: Decimal
}
