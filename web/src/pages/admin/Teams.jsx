import { useState } from 'react'

import Placard, { Row } from '../../components/Placard'
import { Async } from '../../components/States'
import { api } from '../../lib/api'
import { useAsync } from '../../state/useAsync'

/*
  الأسراب والعضويات — و-٧ · FR-083.

  **أرشفة لا حذف، ونقلٌ لا يزوّر التاريخ** (م-١٠): الخادم يرفض أرشفة سرب مأهول
  ونقلًا إلى سرب مؤرشَف — رسالتاهما تُعرضان كما وصلتا.
*/

export default function Teams({ onDone }) {
  const state = useAsync(() => api.teams(), [])

  return (
    <div className="taxi-in mx-auto w-full max-w-[520px] px-4 pt-6 pb-10">
      <header className="mb-5 flex items-baseline gap-3">
        <h1 className="font-display text-[26px] leading-none">الأسراب</h1>
        <span className="centerline" />
        <button
          type="button"
          onClick={onDone}
          className="min-h-[44px] shrink-0 px-2 text-[13px] text-muted"
        >
          رجوع
        </button>
      </header>

      <Async state={state} loadingTitle="الأسراب">
        {(data) => <Body teams={data.teams} onChanged={state.reload} />}
      </Async>
    </div>
  )
}

function Body({ teams, onChanged }) {
  return (
    <div className="flex flex-col gap-4">
      <Placard title="الأسراب القائمة">
        {teams.map((t) => (
          <TeamRow key={t.id} team={t} onChanged={onChanged} />
        ))}
      </Placard>
      <CreateTeamForm onCreated={onChanged} />
      <TransferForm teams={teams} onTransferred={onChanged} />
    </div>
  )
}

function TeamRow({ team, onChanged }) {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function archive() {
    setBusy(true)
    setError('')
    try {
      await api.archiveTeam(team.id)
      onChanged()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mb-2 border-b border-concrete/35 pb-2 last:border-0">
      <Row
        label={`${team.name} (${team.code})`}
        value={`${team.active_members} عضو`}
        tone={team.archived_at ? 'muted' : 'default'}
      />
      {team.archived_at ? (
        <p className="text-[12px] text-muted">مؤرشَف</p>
      ) : (
        <button
          type="button"
          disabled={busy}
          onClick={archive}
          className="mt-1 min-h-[44px] w-full border border-concrete/45 text-[13px] text-muted disabled:opacity-40"
        >
          أرشفة
        </button>
      )}
      {error && (
        <p role="alert" className="mt-1 text-[13px] text-hold">
          {error}
        </p>
      )}
    </div>
  )
}

function CreateTeamForm({ onCreated }) {
  const [name, setName] = useState('')
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit() {
    setBusy(true)
    setError('')
    try {
      await api.createTeam({ name: name.trim(), code: code.trim() })
      setName('')
      setCode('')
      onCreated()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Placard title="سرب جديد">
      <label htmlFor="team_name" className="mb-1.5 block text-[13px]">
        الاسم
      </label>
      <input
        id="team_name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        className="mb-3 min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
      />
      <label htmlFor="team_code" className="mb-1.5 block text-[13px]">
        الرمز
      </label>
      <input
        id="team_code"
        value={code}
        onChange={(e) => setCode(e.target.value)}
        className="mb-3 min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
      />
      {error && (
        <p role="alert" className="mb-3 text-[13px] text-hold">
          {error}
        </p>
      )}
      <button
        type="button"
        disabled={busy || !name.trim() || !code.trim()}
        onClick={submit}
        className="min-h-[48px] w-full border border-taxi bg-taxi text-[16px] text-asphalt disabled:opacity-40"
      >
        {busy ? 'جارٍ الإنشاء…' : 'إنشاء سرب'}
      </button>
    </Placard>
  )
}

function TransferForm({ teams, onTransferred }) {
  const [userId, setUserId] = useState('')
  const [teamId, setTeamId] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const active = teams.filter((t) => !t.archived_at)

  async function submit() {
    setBusy(true)
    setError('')
    try {
      await api.transferMember(teamId, Number(userId))
      setUserId('')
      onTransferred()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Placard title="نقل طالب">
      <label htmlFor="transfer_user" className="mb-1.5 block text-[13px]">
        معرّف الطالب
      </label>
      <input
        id="transfer_user"
        inputMode="numeric"
        value={userId}
        onChange={(e) => setUserId(e.target.value)}
        className="mb-3 min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
      />
      <label htmlFor="transfer_team" className="mb-1.5 block text-[13px]">
        السرب الهدف
      </label>
      <select
        id="transfer_team"
        value={teamId}
        onChange={(e) => setTeamId(e.target.value)}
        className="mb-3 min-h-[48px] w-full border border-concrete/45 bg-taxiway px-3 text-[16px] text-paint"
      >
        <option value="">اختر سربًا</option>
        {active.map((t) => (
          <option key={t.id} value={t.id}>
            {t.name}
          </option>
        ))}
      </select>
      {error && (
        <p role="alert" className="mb-3 text-[13px] text-hold">
          {error}
        </p>
      )}
      <button
        type="button"
        disabled={busy || !userId.trim() || !teamId}
        onClick={submit}
        className="min-h-[48px] w-full border border-taxi bg-taxi text-[16px] text-asphalt disabled:opacity-40"
      >
        {busy ? 'جارٍ النقل…' : 'نقل'}
      </button>
    </Placard>
  )
}
