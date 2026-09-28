import { useState } from 'react'

import { LABEL_OF, type AdminKey } from '../../nav/adminNav'
import { go } from '../../nav/history'
import { useApp } from '../../state/AppState'
import AdminSide, { AdminSideSheet } from './AdminSide'
import { ADMIN_SCREENS } from './registry'

/**
 * قشرة لوحة المشرف — **دائمة**، والشاشة وحدها تتغيّر.
 *
 * `grid-cols-[250px_minmax(0,1fr)]`، و**`minmax(0,1fr)` إلزاميّ**: `1fr`
 * المجرّد هو `minmax(auto,1fr)` فجدولٌ عريض يدفع العمود خارج المنفذ ويُسقط
 * فحصَ الانزياح عند ١٢٨٠px. و`min-w-0` على `<main>` هو الدفاع نفسه طبقةً أدنى.
 *
 * والعمود الأول هو القائمة **يمينًا** لأن المستند RTL وعمود الشبكة الأول هو
 * بداية السطر — مطابقٌ لـ`.admin-side` في النموذج.
 *
 * **و`key={screen}` على الشاشة لا على القشرة:** القشرة نفس نوع العنصر في كل
 * تنقّل فتبقى القائمة مركَّبة — فالمؤشّر **ينزلق** بدل أن يُقاس من الصفر — و
 * `key` يُعيد تركيب الشاشة فيُعاد `useAsync` وتُشتغل حركة الدخول مرّة واحدة.
 *
 * **والمستند يبقى حاوية التمرير:** `<main>` لا يأخذ `overflow-y-auto` أبدًا،
 * وإلّا توقّف `window.scrollTo(0, 0)` في `nav/history.go()` عن العمل صامتًا.
 */
export default function AdminShell({ screen }: { screen: AdminKey }) {
  const { logout } = useApp()
  const [navOpen, setNavOpen] = useState(false)
  const Screen = ADMIN_SCREENS[screen]
  const title = LABEL_OF[screen]

  function select(key: AdminKey) {
    setNavOpen(false)
    go(key)
  }

  function toDeck() {
    setNavOpen(false)
    go('deck')
  }

  return (
    <div className="desk:grid desk:grid-cols-[250px_minmax(0,1fr)]">
      <AdminSide active={screen} onSelect={select} onGoDeck={toDeck} onLogout={logout} />

      <div className="min-w-0">
        {/* شريط الجوّال — يختفي فوق الحدّ حيث القائمة حاضرة دائمًا. */}
        <div className="sticky top-0 z-30 flex min-h-[56px] items-center gap-2 border-b border-(--color-border) bg-(--color-bg-2) px-4 desk:hidden">
          {/* عنوانُ الجوّال هو `h1` نفسه — ولا يُكرَّر أدناه. عنصران أحدهما
              `display:none` دائمًا: المخفيّ يخرج من شجرة الإتاحة، فلا يُقرَأ
              العنوان مرّتين ولا يبقى المستند بلا عنوان. */}
          <h1 className="min-w-0 flex-1 truncate text-[15px] font-bold">{title}</h1>
          <button
            type="button"
            onClick={() => setNavOpen((open) => !open)}
            aria-expanded={navOpen}
            className="min-h-[44px] shrink-0 rounded-(--radius-sm) border border-(--color-border-strong) px-3.5 text-[12px] font-semibold"
          >
            الأقسام
          </button>
        </div>

        {navOpen ? (
          <AdminSideSheet
            active={screen}
            onSelect={select}
            onGoDeck={toDeck}
            onLogout={logout}
          />
        ) : null}

        <main className="mx-auto w-full max-w-[1100px] min-w-0 px-4 pt-4 pb-12 desk:px-6 desk:pt-8">
          <h1 className="hidden text-[18px] font-bold desk:mb-6 desk:block">{title}</h1>
          <Screen key={screen} />
        </main>
      </div>
    </div>
  )
}
