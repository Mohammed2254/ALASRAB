/**
 * الكائن الواحد الذي تراه الشاشات — `api.auth.login(...)` · `api.me.deck()`.
 *
 * التجميع هنا لا في ملفّ واحد ضخم: التقسيم يطابق `api/app/schemas/` فأي
 * انحراف بين الطرفين يظهر في اسم الملفّ نفسه.
 */
import { authApi } from './endpoints/auth'
import { boardsApi } from './endpoints/boards'
import { engagementApi } from './endpoints/engagement'
import { meApi } from './endpoints/me'

export const api = { auth: authApi, me: meApi, boards: boardsApi, engagement: engagementApi }
export { ApiError } from './client'
