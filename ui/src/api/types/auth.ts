/** عقد الجلسة — `POST /auth/login` · `GET /auth/me`. */
import type { Count } from '../brand'

export type Role = 'pilot' | 'admin'

export type Identity = {
  id: Count
  full_name: string
  student_no: string
  role: Role
}

export type Session = { user: Identity }
