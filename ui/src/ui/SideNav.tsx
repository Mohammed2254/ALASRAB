import { useLayoutEffect, useRef, useState } from 'react'

/**
 * التنقّل الجانبيّ المجمَّع — لوحة المشرف.
 *
 * نفس نمط قياس الموضع في `BottomTabs`/`SegmentedControl` لكن **على المحور
 * الرأسيّ**: `useLayoutEffect` فلا قفزة من الصفر عند أوّل رسم (ق-٢٢٩).
 *
 * **والمجموعات الستّ داخل `relative` واحد لا واحدٍ لكلّ مجموعة:** `offsetTop`
 * يُقاس مقابل أقرب سلفٍ موضَّع، فغلافٌ موضَّع لكل مجموعة يُعيد تصفير
 * الإحداثيات ويُوقف المؤشّر عند العنصر الخطأ — وعناوين المجموعات تشارك نفس
 * السياق فتُزيح الحساب.
 *
 * **والمؤشّر ٤٢px داخل زرٍّ ٤٤px** بإزاحة سطرٍ واحد: نسبةُ النموذج محفوظة
 * وأرضيةُ اللمس (ق-٢١٨) تمرّ — لا مساومة بين الاثنين.
 *
 * والحركة `transition-transform` أي CSS محضة، فتخضع مجّانًا لقاعدة تقليل
 * الحركة في `base.css` بلا فحصٍ في `mo.ts`.
 */
// مُعمَّمة على نوع المفتاح: البدائية تبقى عامّة، والمستهلك يحتفظ بمفاتيحه
// الحرفية. ونوعٌ مُرخًى (`key: string`) كان سيُسقط `onSelect` عند المستهلك
// بالتضادّ — مُعالِجٌ يقبل مفاتيح المشرف وحدها لا يصلح حيث يُمرَّر أيّ نصّ.
export type SideNavItem<K extends string = string> = { key: K; label: string }
/** `label: null` = مجموعةٌ بلا عنوان (صدر القائمة). */
export type SideNavGroup<K extends string = string> = {
  label: string | null
  items: readonly SideNavItem<K>[]
}

type Props<K extends string> = {
  groups: readonly SideNavGroup<K>[]
  active: K
  onSelect: (key: K) => void
  /** تسمية الملاحة لقارئ الشاشة — تختلف بين القائمة الجانبية وقائمة الجوّال. */
  label: string
}

export default function SideNav<K extends string>({ groups, active, onSelect, label }: Props<K>) {
  const btnRefs = useRef<Record<string, HTMLButtonElement | null>>({})
  const [thumb, setThumb] = useState<{ top: number } | null>(null)

  useLayoutEffect(() => {
    const btn = btnRefs.current[active]
    if (!btn) {
      // الشاشة النشطة ليست في هذه القائمة (قائمة الجوّال مطويّة مثلًا) —
      // فلا مؤشّر، لا مؤشّرٌ في موضعٍ مضلِّل.
      setThumb(null)
      return
    }
    setThumb({ top: btn.offsetTop })
  }, [active, groups])

  return (
    <nav className="relative flex flex-col" aria-label={label}>
      {thumb ? (
        <span
          aria-hidden="true"
          className="absolute inset-x-0 top-px h-[42px] rounded-(--radius-sm) bg-(--color-accent-tint) transition-transform duration-300 ease-out"
          style={{ transform: `translateY(${thumb.top}px)` }}
        />
      ) : null}

      {groups.map((group, index) => (
        <div
          key={group.label ?? `group-${index}`}
          role="group"
          {...(group.label ? { 'aria-labelledby': `sidenav-h-${index}` } : {})}
        >
          {group.label ? (
            <div
              id={`sidenav-h-${index}`}
              // `--color-text-dim` لا `--color-line`: الثاني نسبته ٢٫٤٦٢ و
              // `VISUAL.md §٢` يقول عنه صريحًا «لا يحمل حرفًا» — وأُعيدت
              // تسميته من `--text-faint` ليصير هذا الخطأ مستحيلًا بالاسم.
              // ووقع مع ذلك هنا نقلًا عن النموذج، وأسقطه قياسُ التباين الحيّ
              // بـ٣٢٠ مخالفة (خمسة عناوين × أربعة مقاسات × كل شاشة إدارية).
              className="px-3 pt-3.5 pb-1.5 text-[11px] text-(--color-text-dim)"
            >
              {group.label}
            </div>
          ) : null}

          {group.items.map((item) => {
            const isActive = item.key === active
            return (
              <button
                key={item.key}
                data-key={item.key}
                ref={(el) => {
                  btnRefs.current[item.key] = el
                }}
                type="button"
                onClick={() => onSelect(item.key)}
                aria-current={isActive ? 'page' : undefined}
                className={`relative flex min-h-[44px] w-full items-center rounded-(--radius-sm) px-3 text-start text-[13px] font-semibold ${
                  isActive ? 'text-(--color-accent)' : 'text-(--color-text-dim)'
                }`}
              >
                {item.label}
              </button>
            )
          })}
        </div>
      ))}
    </nav>
  )
}
