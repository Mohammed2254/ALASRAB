import HexIcon from '../../ui/HexIcon'
import SideNav from '../../ui/SideNav'
import { GLYPHS } from '../../ui/glyphs'
import { ADMIN_NAV, type AdminKey } from '../../nav/adminNav'

/**
 * قائمة لوحة المشرف — هويةٌ وتنقّلٌ وذيل.
 *
 * **فوق ١٠٢٤px:** عمود ٢٥٠px لاصق بارتفاع المنفذ، **بتمرير داخليّ**. والتمرير
 * ليس اختياريًّا: ستّ عشرة وجهة × ٤٤px + خمسة عناوين + الهوية + الذيل ≈
 * ٩٩٠px مقابل منفذٍ ٨٠٠px — مقيسٌ حيًّا لا مقدَّرًا. وهو تمريرٌ **رأسيّ**
 * فلا يخصّه فحصُ الانزياح الأفقيّ.
 *
 * **تحت الحدّ:** شريطٌ لاصق بزرّ «الأقسام» يفتح **نفس القائمة ممتدّةً في
 * السياق** تدفع المحتوى لأسفل. ورفضتُ الدرج المنزلق عمدًا: لا بوّابة ولا
 * حاجز شفّاف ولا حصر تركيز ولا قفل تمرير ولا اعتراض زرّ الرجوع — والأهمّ أن
 * الحاجز الشفّاف يُدخل كل ما تحته في مسار قياس التباين، و`backdrop-filter`
 * ممنوع بلا أرضية معتمة في الكتلة نفسها (`check-opaque-floor`). واللوحة في
 * السياق `bg-(--color-bg-2)` — معتمةٌ ببنيتها فالتباين قابل للقياس.
 *
 * **والهوية كتلةٌ ساكنة لا مبدّل:** النموذج نفسه يقول عن مبدّل السرب
 * `toast('خارج نطاق هذا العرض')`، ولا حقل `org` في `Identity`، ودورُ المشرف
 * على مستوى المنظّمة أصلًا (`AGENTS.md` ٩). فزرٌّ بلا وجهة أسوأ من نصٍّ صادق.
 */
type Props = {
  active: AdminKey
  onSelect: (key: AdminKey) => void
  onGoDeck: () => void
  onLogout: () => void
}

const footerClass =
  'flex min-h-[44px] w-full items-center rounded-(--radius-sm) px-3 text-start text-[13px] font-semibold text-(--color-text-dim)'

function Identity() {
  return (
    <div className="flex items-center gap-2.5 px-3 pb-3">
      <HexIcon size={22} glyph={GLYPHS.home} filled />
      <span className="text-[14px] font-bold">الأسراب</span>
    </div>
  )
}

function Footer({ onGoDeck, onLogout }: { onGoDeck: () => void; onLogout: () => void }) {
  return (
    <div className="mt-3 border-t border-(--color-border) pt-2">
      {/* «بطاقتي» زيادةٌ مقصودة على النموذج: المشرف طيّارٌ أيضًا، وشبكة
          البلاطات الإدارية حُذفت — فبدونه لا طريق له إلى بطاقته إلا زرّ
          المتصفّح. */}
      <button type="button" onClick={onGoDeck} className={footerClass}>
        بطاقتي
      </button>
      <button type="button" onClick={onLogout} className={footerClass}>
        تسجيل الخروج
      </button>
    </div>
  )
}

export default function AdminSide({ active, onSelect, onGoDeck, onLogout }: Props) {
  return (
    <aside className="hidden border-s border-(--color-border) bg-(--color-bg-2) px-3 py-5 desk:sticky desk:top-0 desk:block desk:h-dvh desk:overflow-y-auto">
      <Identity />
      <SideNav groups={ADMIN_NAV} active={active} onSelect={onSelect} label="أقسام الإدارة" />
      <Footer onGoDeck={onGoDeck} onLogout={onLogout} />
    </aside>
  )
}

/** القائمة نفسها تحت الحدّ — تُفتح في السياق من شريط الشاشة. */
export function AdminSideSheet({ active, onSelect, onGoDeck, onLogout }: Props) {
  return (
    <div className="border-b border-(--color-border) bg-(--color-bg-2) px-3 py-3 desk:hidden">
      <SideNav groups={ADMIN_NAV} active={active} onSelect={onSelect} label="أقسام الإدارة" />
      <Footer onGoDeck={onGoDeck} onLogout={onLogout} />
    </div>
  )
}
