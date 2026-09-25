/**
 * الإطار السداسي — علامة الهوية (ADR: و-١٣، `VISUAL.md §١`).
 *
 * بدائية بصرية خالصة: هندسة SVG بلا أي حقل مجال. ولذلك تُفحص بقاعدة
 * `VISUAL_PRIMITIVES` (لا تذكر حقلًا) لا بقاعدة الشاشات (لا تحسب).
 */
type Props = { size?: number; glyph: string; filled?: boolean; label?: string }

export default function HexIcon({ size = 40, glyph, filled = false, label }: Props) {
  const stroke = filled ? 'var(--color-on-accent)' : 'var(--color-accent)'
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      role={label ? 'img' : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <path
        d="M20 6 L44 6 L58 32 L44 58 L20 58 L6 32 Z"
        fill={filled ? 'var(--color-accent)' : 'var(--color-accent-tint)'}
        stroke="var(--color-accent)"
        strokeWidth="3"
      />
      <path d={glyph} fill="none" stroke={stroke} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
