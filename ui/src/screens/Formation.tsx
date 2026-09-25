import { useState } from 'react'

import { api } from '../api'
import type { FormationScope } from '../api/types/boards'
import { useAsync } from '../state/useAsync'
import { Async } from '../ui/Async'
import EmptyState from '../ui/EmptyState'
import FormationSky from '../ui/FormationSky'
import Placard from '../ui/Placard'
import SegmentedControl from '../ui/SegmentedControl'

/**
 * مشهد التشكيل — `GET /boards/formation?scope=` (FR-053). **تراكميّ لا
 * نافذة أسبوع** (`API.md`، تمييزٌ متعمَّد عن لوحتَي الأفراد/الأسراب).
 * `size_pct` يصل جاهزًا للعرض — لا حساب هنا (`check-no-domain-logic.mjs`).
 */

const SCOPES = [
  { key: 'team', label: 'سربي' },
  { key: 'general', label: 'عامّ' },
]

export default function Formation() {
  const [scope, setScope] = useState<FormationScope>('team')
  const state = useAsync(() => api.boards.formation(scope), [scope])

  return (
    <div>
      <SegmentedControl options={SCOPES} value={scope} onChange={(key) => setScope(key as FormationScope)} />
      <p className="mb-3.5 text-[13px] text-(--color-text-dim)">
        طول شريط كل طيّار يمثّل ساعات طيرانه — كلّما طال الشريط، زادت ساعاته.
      </p>

      <Async state={state} loadingTitle="مشهد التشكيل">
        {(data) => {
          const flying = data.aircraft.filter((a) => !a.grounded)
          const landed = data.aircraft.filter((a) => a.grounded)
          return data.aircraft.length ? (
            <Placard title="التشكيل">
              <FormationSky
                flying={flying.map((a) => ({ name: a.name ?? 'طيّار', pct: a.size_pct, value: a.size }))}
                landed={landed.map((a) => ({ name: a.name ?? 'طيّار', pct: a.size_pct, value: a.size }))}
              />
            </Placard>
          ) : (
            <Placard title="التشكيل">
              <EmptyState>لا طيّارين في هذا المشهد بعد.</EmptyState>
            </Placard>
          )
        }}
      </Async>
    </div>
  )
}
