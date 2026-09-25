import { useState } from 'react'

import { api } from '../api'
import { useAsync } from '../state/useAsync'
import { Async } from '../ui/Async'
import EmptyState from '../ui/EmptyState'
import Placard from '../ui/Placard'
import Podium, { type BoardEntry } from '../ui/Podium'
import SegmentedControl from '../ui/SegmentedControl'

/**
 * الصدارة — `GET /boards/{pilots,teams}` (FR-050..052)، **نافذة الأسبوع
 * الحالي** (تصحّ خلافًا للتشكيل التراكميّ — `و-١٥.md` §١.١). `chg` غائبة
 * عمدًا: لا سند لها في العقد (`Podium.chg` اختيارية منذ هذه الشريحة).
 *
 * **قرار المنصّة مقابل قائمة عادية يعيش داخل `Podium` نفسها** (و-١٥) — قرارٌ
 * عرضيّ لا حسابيّ، فمكانه البدائية لا الشاشة الممنوعة من استيراد `motion/`.
 */

type Tab = 'pilots' | 'teams'
const TABS = [
  { key: 'pilots', label: 'الأفراد' },
  { key: 'teams', label: 'الأسراب' },
]

function PilotsBoard() {
  const state = useAsync(() => api.boards.pilots(), [])
  return (
    <Async state={state} loadingTitle="صدارة الأفراد">
      {(data) => {
        const entries: BoardEntry[] = data.pilots.map((p) => ({ name: p.full_name, value: p.hours }))
        return <Board entries={entries} label="طيّارًا هذا الأسبوع" />
      }}
    </Async>
  )
}

function TeamsBoard() {
  const state = useAsync(() => api.boards.teams(), [])
  return (
    <Async state={state} loadingTitle="صدارة الأسراب">
      {(data) => {
        const entries: BoardEntry[] = data.teams.map((t) => ({ name: t.team, tag: t.code, value: t.avg_hours }))
        return <Board entries={entries} label="أسراب — بالمعدّل" />
      }}
    </Async>
  )
}

function Board({ entries, label }: { entries: BoardEntry[]; label: string }) {
  if (entries.length === 0) {
    return (
      <Placard title="الصدارة">
        <EmptyState>لا بيانات لهذا الأسبوع بعد.</EmptyState>
      </Placard>
    )
  }

  return (
    <div>
      <p className="mb-4 text-center text-[12px] text-(--color-text-dim)">
        <bdi dir="ltr">{entries.length}</bdi> {label}
      </p>
      <Podium entries={entries} />
    </div>
  )
}

export default function Boards() {
  const [tab, setTab] = useState<Tab>('pilots')
  return (
    <div>
      <SegmentedControl options={TABS} value={tab} onChange={(key) => setTab(key as Tab)} />
      {tab === 'pilots' ? <PilotsBoard /> : <TeamsBoard />}
    </div>
  )
}
