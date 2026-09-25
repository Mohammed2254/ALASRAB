import type { ButtonHTMLAttributes } from 'react'

/** زرٌّ بثلاث لهجات: أساسيّ مصمت · مفرَّغ · مفرَّغ سلبيّ. */
type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'outline' | 'danger'
}

const VARIANT_CLASS: Record<NonNullable<Props['variant']>, string> = {
  primary: 'bg-(--color-accent) text-(--color-on-accent)',
  outline: 'border border-(--color-border-strong) bg-transparent text-(--color-text)',
  danger: 'border border-(--color-red) bg-transparent text-(--color-red-text)',
}

export default function Button({ variant = 'primary', className = '', type = 'button', ...rest }: Props) {
  return (
    <button
      type={type}
      className={`min-h-[44px] rounded-(--radius-sm) px-5 text-[13px] font-bold disabled:opacity-40 ${VARIANT_CLASS[variant]} ${className}`}
      {...rest}
    />
  )
}
