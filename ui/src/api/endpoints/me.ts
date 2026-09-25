/** بطاقة الطيّار وسجلّ ساعاته — `GET /me/deck` · `GET /me/events`. */
import { request } from '../client'
import type { Deck, LedgerEvent } from '../types/me'

export const meApi = {
  deck: () => request<Deck>('/me/deck'),
  events: (limit = 20) => request<{ events: LedgerEvent[] }>(`/me/events?limit=${limit}`),
}
