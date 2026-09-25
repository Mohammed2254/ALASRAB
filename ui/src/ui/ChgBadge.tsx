import { chgDirection } from '../motion/geometry'

const ARROW = { up: '▲', down: '▼', same: '–' } as const
const CLASS = {
  up: 'text-(--color-green)',
  down: 'text-(--color-red-text)',
  same: 'text-(--color-text-dim)',
} as const

/** ▲/▼/– تغيّر ترتيب — الاتّجاه والمقدار من `motion/geometry.ts`. */
export default function ChgBadge({ chg }: { chg: number }) {
  const { direction, magnitude } = chgDirection(chg)
  return (
    <span className={`inline-flex items-center gap-0.5 text-[10px] font-bold ${CLASS[direction]}`}>
      {ARROW[direction]}
      {direction !== 'same' ? <bdi dir="ltr">{magnitude}</bdi> : null}
    </span>
  )
}
