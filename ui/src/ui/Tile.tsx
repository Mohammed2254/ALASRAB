import HexIcon from './HexIcon'

/** بلاطة أيقونة+تسمية قابلة للنقر — شبكة الوصول السريع في بطاقة الطيّار. */
type Props = { glyph: string; label: string; onClick: () => void }

export default function Tile({ glyph, label, onClick }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex min-h-[44px] flex-col items-center gap-2.5 rounded-(--radius-md) border border-(--color-border) bg-(--color-surface) p-4.5 text-center"
    >
      <HexIcon size={32} glyph={glyph} />
      <span className="text-[13px] font-semibold">{label}</span>
    </button>
  )
}
