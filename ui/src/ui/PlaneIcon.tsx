/** طائرة ورقية بسيطة — تُستعمل في التشكيل وشريط التقدّم وإرسال الملاحظة. */
type Props = { size: number; color?: string }

export default function PlaneIcon({ size, color = 'var(--color-accent)' }: Props) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden="true">
      <path d="M24 4 L38 43 L24 34 L10 43 Z" fill={color} />
    </svg>
  )
}
