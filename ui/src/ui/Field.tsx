import type { ReactNode } from 'react'

/**
 * أصنافُ المُدخَل القياسيّ — **مُصدَّرةٌ من هنا لأنها كانت مكرَّرةً عشرين
 * مرّةً** في تسعة عشر ملفًّا (ستّ عشرة منها `const fieldClass` بنفس النصّ
 * حرفيًّا، وثلاثٌ تُدرجه داخل `className`). وموضعُها هنا لا في ملفٍّ مستقلّ
 * لأن أربعة عشر من تلك الملفّات تستورد `Field` أصلًا — فلا سطرَ استيرادٍ
 * جديدًا.
 *
 * و`min-h-[48px]` لا ٤٤: حدُّ اللمس ٤٤ (ق-١٤)، والأربعُ الزائدة هامشُ أمانٍ
 * لحقلٍ يُضغط بإصبعٍ لا بمؤشّر.
 */
export const fieldClass =
  'min-h-[48px] w-full rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) px-3 text-[16px] text-(--color-text)'

/**
 * صفٌّ مضغوط داخل جدولٍ أو شبكة — أقصرُ من `fieldClass` وبلا عرضٍ كامل.
 * كان مكرَّرًا أربع مرّات، اثنتان منها متطابقتان حرفيًّا.
 */
export const rowInputClass =
  'min-h-[44px] rounded-(--radius-sm) border border-(--color-border-strong) bg-(--color-bg-2) px-2 text-[14px] text-(--color-text)'

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
