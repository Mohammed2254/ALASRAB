/**
 * الكائن الواحد الذي تراه الشاشات — `api.auth.login(...)` · `api.me.deck()`.
 *
 * التجميع هنا لا في ملفّ واحد ضخم: التقسيم يطابق `api/app/schemas/` فأي
 * انحراف بين الطرفين يظهر في اسم الملفّ نفسه.
 */
import { authApi } from './endpoints/auth'
import { meApi } from './endpoints/me'

export const api = { auth: authApi, me: meApi }
export { ApiError } from './client'
