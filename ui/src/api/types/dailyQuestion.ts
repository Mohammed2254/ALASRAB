/**
 * سؤال اليوم — الشقّ الإداريّ، من `schemas/daily_question.py` (و-٢١).
 *
 * الشقّ الطيّاريّ في `types/me.ts` — مقسَّمان بحسب من يراهما، نفس منطق
 * `types/adminQueue.ts` مقابل `me.ts`.
 */
import type { Count, Decimal } from '../brand'

export type QuestionChoice = { id: Count; text: string }

export type QuestionRow = {
  id: Count
  day: string
  prompt: string
  choices: QuestionChoice[]
  correct_id: Count
  note: string
  reward_hours: Decimal
  answers: Count
  /**
   * **حقلٌ من الخادم لا استنتاجٌ من `answers`**: «مُقفَل» قاعدةٌ (ث-١٧) لا
   * عرض — سؤالٌ أُجيب لا يُعدَّل ولا يُحذَف، لأن `answers.correct` و
   * `point_event_id` لا يفترقان وقد كُتبا معًا.
   *
   * والمقارنة هنا تُسقطها بوّابة AST أصلًا.
   */
  locked: boolean
}

export type QuestionsList = { questions: QuestionRow[] }

/** نموذج الإنشاء كما يكتبه المشرف — النصوص خام حتى الحفظ (نمط نماذج و-١٧). */
export type QuestionChoiceForm = { id: number; text: string }
export type QuestionForm = {
  day: string
  prompt: string
  choices: QuestionChoiceForm[]
  correct_id: string
  note: string
  reward_hours: string
}
export type QuestionRef = { id: Count; day: string }
