import { useState } from 'react'

import { api, ApiError } from '../../api'
import type { AdminTeamRow } from '../../api/types/teams'
import { useAsync } from '../../state/useAsync'
import { Async } from '../../ui/Async'
import Button from '../../ui/Button'
import Field from '../../ui/Field'
import Placard from '../../ui/Placard'
import Prow from '../../ui/Prow'

/**
 * الأسراب والعضويات — `GET/POST /admin/teams*` (FR-083). **أرشفة لا حذف،
 * ونقلٌ لا يزوّر التاريخ** (م-١٠): رسالة الخادم عند رفض أرشفة سرب مأهول أو
 * نقلٍ إلى سرب مؤرشَف تُعرض كما وصلت، بلا فحص هنا.
 */
const fieldClass =
  'min-h-[48px] w-full rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) px-3 text-[16px] text-(--color-text)'

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
      {error ? (
        <p role="alert" className="mt-1 text-[13px] text-(--color-red-text)">
          {error}
        </p>
      ) : null}
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
      {error ? (
        <p role="alert" className="mb-3 text-[13px] text-(--color-red-text)">
          {error}
        </p>
      ) : null}
      <Button disabled={busy || !name.trim() || !code.trim()} onClick={submit} className="w-full">
        {busy ? 'جارٍ الإنشاء…' : 'إنشاء سرب'}
      </Button>
    </Placard>
  )
}

function TransferForm({ teams, onTransferred }: { teams: AdminTeamRow[]; onTransferred: () => void }) {
  const [userId, setUserId] = useState('')
  const [teamId, setTeamId] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const active = teams.filter((t) => !t.archived_at)

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
    <Placard title="نقل طالب">
      <Field label="معرّف الطالب" htmlFor="transfer_user">
        <input id="transfer_user" inputMode="numeric" value={userId} onChange={(e) => setUserId(e.target.value)} className={fieldClass} />
      </Field>
      <Field label="السرب الهدف" htmlFor="transfer_team">
        <select id="transfer_team" value={teamId} onChange={(e) => setTeamId(e.target.value)} className={fieldClass}>
          <option value="">اختر سربًا</option>
          {active.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
      </Field>
      {error ? (
        <p role="alert" className="mb-3 text-[13px] text-(--color-red-text)">
          {error}
        </p>
      ) : null}
      <Button disabled={busy || !userId.trim() || !teamId} onClick={submit} className="w-full">
        {busy ? 'جارٍ النقل…' : 'نقل'}
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
            <TransferForm teams={data.teams} onTransferred={state.reload} />
          </div>
        )}
      </Async>
    </div>
  )
}
