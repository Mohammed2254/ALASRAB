import type { ReactNode } from 'react'

/** غلاف حقل نموذج: تسمية + مُدخَل (عبر `children`) + نصّ مساعدة اختياريّ. */
type Props = {
  label: string
  htmlFor?: string
  helper?: ReactNode
  children: ReactNode
}

export default function Field({ label, htmlFor, helper, children }: Props) {
  return (
    <div className="mb-3.5">
      <label htmlFor={htmlFor} className="mb-1.5 block text-[12px] font-semibold text-(--color-text-dim)">
        {label}
      </label>
      {children}
      {helper ? <p className="mt-1.5 text-[11px] text-(--color-text-dim)">{helper}</p> : null}
    </div>
  )
}
