/** مسارات الجلسة — `POST /auth/login` · `POST /auth/logout` · `GET /auth/me`. */
import { request } from '../client'
import type { Session } from '../types/auth'

export const authApi = {
  login: (studentNo: string, pin: string) =>
    request<Session>('/auth/login', { method: 'POST', body: { student_no: studentNo, pin } }),
  // الخروج **بلا حارس جلسة** عمدًا: جلسةٌ منتهية يجب أن تُخرج المستخدم لا أن
  // تحبسه في شاشة لا يستطيع مغادرتها.
  logout: () => request<null>('/auth/logout', { method: 'POST' }),
  me: () => request<Session>('/auth/me'),
}
