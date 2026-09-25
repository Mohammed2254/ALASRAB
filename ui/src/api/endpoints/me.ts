/**
 * شاشات الطيّار الذاتية — البطاقة والقراءات ومحطة التزوّد. مُجمَّعة في ملفٍّ
 * واحد لأن `routes/me.py` نفسه يجمعها فعليًّا (`و-١٥.md` §٢ قرار ٣) رغم
 * تفرّق مخطّطاتها بين `schemas/me.py` و`schemas/fuel.py`.
 */
import { request } from '../client'
import type { Deck, LedgerEvent, MyReading, Station, SubmitReading, SubmitReadingForm } from '../types/me'

export const meApi = {
  deck: () => request<Deck>('/me/deck'),
  events: (limit = 20) => request<{ events: LedgerEvent[] }>(`/me/events?limit=${limit}`),
  readings: () => request<{ readings: MyReading[] }>('/me/readings'),
  // `pages` نصٌّ في النموذج ← رقمٌ في الجسم السلكيّ. التحويل هنا لا في الشاشة
  // (`SubmitReadingForm` doc في `types/me.ts`).
  submitReading: (form: SubmitReadingForm) => {
    const body: SubmitReading = { ...form, pages: Number(form.pages) }
    return request<{ id: number; status: string }>('/me/readings', { method: 'POST', body })
  },
  station: () => request<Station>('/station'),
}
