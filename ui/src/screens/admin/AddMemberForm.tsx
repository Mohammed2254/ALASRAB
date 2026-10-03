import { useState } from 'react'

import { api, ApiError } from '../../api'
import type { AdminTeamRow } from '../../api/types/teams'
import Button from '../../ui/Button'
import Field from '../../ui/Field'
import Placard from '../../ui/Placard'

const fieldClass =
  'min-h-[48px] w-full rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) px-3 text-[16px] text-(--color-text)'

/**
 * «اختر طالبًا لإضافته…» + «إضافة» — النموذج المعتمد (و-٢١).
 *
 * كان حقلَ **معرّفٍ رقميّ** يكتبه المشرف بيده: رقمٌ لا يراه في أيّ شاشة
 * (السجلّ يعرض رقم الطالب لا معرّف الصفّ)، فكان عمليًّا غير قابل للاستعمال —
 * وكل خطأ فيه ينقل الطالب الخطأ بلا أن يُنبّه أحد، لأن أيّ معرّفٍ قائم صالح.
 *
 * **والأسماء تأتي من `data.teams` نفسها** لا بنداءٍ ثانٍ: `list_teams` يُرجع
 * الأعضاء كاملين أصلًا (و-٢٠). ولذلك **لا تظهر فيها إلا من له عضوية سارية** —
 * وهذا صحيح لهذه الشاشة: من لا سرب له يُسنَد سربُه من شاشة الطلاب لحظة إنشائه.
 *
 * والفعل **نقلٌ لا إضافة** في الخلفية (`transfer_member`): العضوية القديمة
 * تُغلَق لا تُحذَف، فأحداث الطالب تبقى منسوبةً كما وقعت (م-١٠).
 */
export default function AddMemberForm({ teams, onTransferred }: { teams: AdminTeamRow[]; onTransferred: () => void }) {
  const [userId, setUserId] = useState('')
  const [teamId, setTeamId] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const active = teams.filter((t) => !t.archived_at)

  // كل الطلاب مع سربهم الحاليّ — فيرى المشرف من أين يَنقل قبل أن ينقل.
  const candidates = teams.flatMap((t) => t.members.map((m) => ({ ...m, from: t.name })))
  const chosen = candidates.find((c) => String(c.user_id) === userId)
  const target = active.find((t) => String(t.id) === teamId)

  async function submit() {
    setBusy(true)
    setError('')
    try {
      await api.admin.transferMember(teamId, userId)
      setUserId('')
      onTransferred()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Placard title="إضافة طالب إلى سرب">
      <Field label="الطالب" htmlFor="member_user">
        <select
          id="member_user"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          className={fieldClass}
        >
          <option value="">اختر طالبًا لإضافته…</option>
          {candidates.map((c) => (
            <option key={c.user_id} value={c.user_id}>
              {c.full_name} — {c.from}
            </option>
          ))}
        </select>
      </Field>
      <Field label="السرب الهدف" htmlFor="member_team">
        <select
          id="member_team"
          value={teamId}
          onChange={(e) => setTeamId(e.target.value)}
          className={fieldClass}
        >
          <option value="">اختر سربًا</option>
          {active.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
      </Field>

      {/* **تأكيدٌ بالاسم قبل الفعل:** النقل يُغلق عضويةً ويفتح أخرى، وهو
          أثرٌ لا يُرى في الشاشة فورًا — فجملةٌ صريحة أرخص من تراجع. */}
      {chosen && target ? (
        <p className="mb-3 text-[13px] text-(--color-text-dim)">
          يُنقل <bdi>{chosen.full_name}</bdi> من «{chosen.from}» إلى «{target.name}».
        </p>
      ) : null}

      {error ? (
        <p role="alert" className="mb-3 text-[13px] text-(--color-red-text)">
          {error}
        </p>
      ) : null}
      <Button disabled={busy || !userId || !teamId} onClick={submit} className="w-full">
        {busy ? 'جارٍ النقل…' : 'إضافة'}
      </Button>
    </Placard>
  )
}
