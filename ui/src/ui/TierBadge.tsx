/**
 * شارة الرتبة — شيفرون ← شيفرونان ← شيفرون بأجنحة ← نجمة بأجنحة.
 *
 * **السلسلة أطول من السُّلّم عمدًا** (`VISUAL.md §٥`): أربع رتب اليوم وستزيد،
 * والزائد يأخذ أعلاها بدل أن يختفي. والاختيار بالفهرس لا بمقارنة — فالمقارنة
 * ممنوعة في هذه الطبقة، والحدّ يُفرض بـ`Math` داخل `motion/` لا هنا.
 */
import HexIcon from './HexIcon'

const MARKS = [
  'M24 38 L32 28 L40 38',
  'M24 34 L32 25 L40 34 M24 44 L32 35 L40 44',
  'M26 36 L32 29 L38 36 M10 34 L22 30 M54 34 L42 30',
  'M32 14 L35.5 20 L32 26 L28.5 20 Z M6 36 L24 28 M58 36 L40 28',
] as const

type Props = { tier: number; size?: number; label?: string | undefined }

export default function TierBadge({ tier, size = 28, label }: Props) {
  const glyph = MARKS.at(tier - 1) ?? MARKS.at(-1) ?? MARKS[0]
  return <HexIcon size={size} glyph={glyph} filled={tier === MARKS.length} label={label} />
}
