import { useState } from 'react'

import { api, ApiError } from '../../api'
import type { AdminTeamRow } from '../../api/types/teams'
import { useAsync } from '../../state/useAsync'
import { Async } from '../../ui/Async'
import Button from '../../ui/Button'
import Field, { fieldClass } from '../../ui/Field'
import Placard from '../../ui/Placard'
import Prow from '../../ui/Prow'
import AddMemberForm from './AddMemberForm'
import ErrorText from '../../ui/ErrorText'

/**
 * الأسراب والعضويات — `GET/POST /admin/teams*` (FR-083). **أرشفة لا حذف،
 * ونقلٌ لا يزوّر التاريخ** (م-١٠): رسالة الخادم عند رفض أرشفة سرب مأهول أو
 * نقلٍ إلى سرب مؤرشَف تُعرض كما وصلت، بلا فحص هنا.
 */

function TeamRow({ team, onChanged }: { team: AdminTeamRow; onChanged: () => void }) {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function archive() {
    setBusy(true)
    setError('')
    try {
      await api.admin.archiveTeam(team.id)
      onChanged()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mb-2 border-b border-(--color-border) pb-2 last:border-none">
      <Prow label={`${team.name} (${team.code})`} value={`${team.active_members} عضو`} />

      {/* الأسماء لا العدد وحده — «٩ عضو» بلا أسماء لا يُدار به سرب. */}
      {team.members.length ? (
        <ul className="mt-1 mb-2 flex flex-wrap gap-x-3 gap-y-1 text-[12px] text-(--color-text-dim)">
          {team.members.map((m) => (
            <li key={m.user_id}>
              {m.full_name} <bdi dir="ltr">({m.student_no})</bdi>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-1 mb-2 text-[12px] text-(--color-text-dim)">لا أعضاء في هذا السرب.</p>
      )}

      {team.archived_at ? (
        <p className="text-[12px] text-(--color-text-dim)">مؤرشَف</p>
      ) : (
        <button
          type="button"
          disabled={busy}
          onClick={archive}
          className="mt-1 min-h-[44px] w-full rounded-(--radius-sm) border border-(--color-border-strong) text-[13px] text-(--color-text-dim) disabled:opacity-40"
        >
          أرشفة
        </button>
      )}
      {error ? <ErrorText spacing="mt-1">{error}</ErrorText> : null}
    </div>
  )
}

function CreateTeamForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit() {
    setBusy(true)
    setError('')
    try {
      await api.admin.createTeam({ name: name.trim(), code: code.trim() })
      setName('')
      setCode('')
      onCreated()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقّع.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Placard title="سرب جديد">
      <Field label="الاسم" htmlFor="team_name">
        <input id="team_name" value={name} onChange={(e) => setName(e.target.value)} className={fieldClass} />
      </Field>
      <Field label="الرمز" htmlFor="team_code">
        <input id="team_code" value={code} onChange={(e) => setCode(e.target.value)} className={fieldClass} />
      </Field>
      {error ? <ErrorText>{error}</ErrorText> : null}
      <Button disabled={busy || !name.trim() || !code.trim()} onClick={submit} className="w-full">
        {busy ? 'جارٍ الإنشاء…' : 'إنشاء سرب'}
      </Button>
    </Placard>
  )
}

export default function Teams() {
  const state = useAsync(() => api.admin.teams(), [])

  return (
    <div className="flex flex-col gap-3.5">
      <Async state={state} loadingTitle="الأسراب">
        {(data) => (
          <div className="flex flex-col gap-3.5">
            <Placard title="الأسراب القائمة">
              {data.teams.map((t) => (
                <TeamRow key={t.id} team={t} onChanged={state.reload} />
              ))}
            </Placard>
            <CreateTeamForm onCreated={state.reload} />
            <AddMemberForm teams={data.teams} onTransferred={state.reload} />
          </div>
        )}
      </Async>
    </div>
  )
}
