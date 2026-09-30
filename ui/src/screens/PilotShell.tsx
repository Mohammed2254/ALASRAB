import { useEffect } from 'react'
import type { ReactNode } from 'react'

import { go } from '../nav/history'
import type { ScreenKey } from '../nav/routes'
import { useApp } from '../state/AppState'
import { preloadAdminWhenIdle } from './admin/lazy'
import BottomTabs, { type Tab } from '../ui/BottomTabs'
import { GLYPHS } from '../ui/glyphs'

/**
 * قشرة شاشات الطيّار الخمس (البطاقة · القراءات · محطة التزوّد · التشكيل ·
 * الصدارة) — شريط تبويب ثابت + شريط هوية علويّ. **بلا اسم السرب في الترويسة
 * عمدًا**: يتطلّب جلب `/me/deck` على كل شاشة لعرض تسمية واحدة — تكلفةٌ على
 * الأداء بلا فائدة وظيفية؛ اسم السرب يظهر داخل محتوى البطاقة ومحطة التزوّد
 * حيث يصل مجّانًا مع البيانات المطلوبة أصلًا.
 */
const TABS: Tab[] = [
  { key: 'station', label: 'الوقود', glyph: GLYPHS.fuel },
  { key: 'formation', label: 'التشكيل', glyph: GLYPHS.formation },
  { key: 'board', label: 'الصدارة', glyph: GLYPHS.board },
  { key: 'readings', label: 'قراءاتي', glyph: GLYPHS.book },
  { key: 'deck', label: 'الرئيسية', glyph: GLYPHS.home },
]

export default function PilotShell({ active, children }: { active: ScreenKey; children: ReactNode }) {
  const { user, logout } = useApp()

  // تسخينُ جزء المشرف على السكون **لمن دورُه مشرف وحده** — الطالب لا ينزّله
  // أبدًا. ويقع بعد أوّل رسم فلا يزاحمه.
  useEffect(() => {
    if (user?.role === 'admin') preloadAdminWhenIdle()
  }, [user?.role])

  return (
    <div className="mx-auto w-full max-w-[520px] px-4 pt-6 pb-24">
      <header className="mb-5 flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={logout}
          className="min-h-[44px] min-w-[44px] shrink-0 px-3 text-[13px] text-(--color-text-dim)"
        >
          خروج
        </button>
        <span className="text-[16px] font-bold">{user?.full_name}</span>
      </header>

      {children}

      <BottomTabs tabs={TABS} active={active} onSelect={(key) => go(key as ScreenKey)} />
    </div>
  )
}
