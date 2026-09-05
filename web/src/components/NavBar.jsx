/*
  شريط تنقّل بطاقة الطيّار — و-٩أ.

  **قائمة بيانات لا سلسلة أزرار مكتوبة يدويًّا.** كانت كل وحدة (و-٤ زرًّا
  واحدًا، و-٧ خمسة، و-٨ ثلاثة) تضيف كتلة JSX مكرَّرة إلى `PilotDeck.jsx` حتى
  بلغ ٣٨٦ سطرًا — أكثر من ٢٫٥× حدّ المراجعة في `AGENTS.md`. و-٩ ستضيف ٥-٧
  شاشات أخرى؛ الإضافة هنا **سطرٌ واحد في `NAV_ITEMS`** لا كتلة جديدة
  (`docs/slices/و-٩.md` §المرحلة ٩أ).

  **لا معرفة بحقول المجال هنا** — `isAdmin` قيمة دور لا رقمًا ماليًّا، فهذا
  الملفّ خارج نطاق `check-no-domain-logic.mjs` عمدًا (لا `CONTRACT_CONSUMERS`
  ولا `VISUAL_PRIMITIVES`): لا يرى `hours` ولا `progress_pct` ولا أيّ حقل
  من عقد `/me/deck` إطلاقًا.

  **الدور من الخادم لا من الواجهة** — إخفاء الزرّ راحةٌ لا حماية، والصلاحية
  محروسة بـ`@admin_required`/`@login_required` في كل مسار على حدة.
*/

const NAV_ITEMS = [
  { key: 'readings', label: 'قراءاتي', tone: 'primary', adminOnly: false },
  { key: 'station', label: 'محطة التزوّد', tone: 'secondary', adminOnly: false },
  { key: 'pilotsBoard', label: 'صدارة الأفراد', tone: 'secondary', adminOnly: false },
  { key: 'teamsBoard', label: 'صدارة الأسراب', tone: 'secondary', adminOnly: false },
  { key: 'formation', label: 'مشهد التشكيل', tone: 'secondary', adminOnly: false },
  { key: 'question', label: 'سؤال اليوم', tone: 'secondary', adminOnly: false },
  { key: 'weekPilot', label: 'طيار الأسبوع', tone: 'secondary', adminOnly: false },
  { key: 'submitNote', label: 'أرسل ملاحظة', tone: 'secondary', adminOnly: false },
  { key: 'queue', label: 'طابور القراءات', tone: 'secondary', adminOnly: true },
  { key: 'report', label: 'التقرير الدوري', tone: 'secondary', adminOnly: true },
  { key: 'weights', label: 'الأوزان', tone: 'secondary', adminOnly: true },
  { key: 'thresholds', label: 'العتبات', tone: 'secondary', adminOnly: true },
  { key: 'teams', label: 'الأسراب', tone: 'secondary', adminOnly: true },
  { key: 'audit', label: 'سجلّ التغييرات', tone: 'secondary', adminOnly: true },
  { key: 'fuelActivities', label: 'أنشطة الوقود', tone: 'secondary', adminOnly: true },
  { key: 'fuelAssess', label: 'تقييم نشاط', tone: 'secondary', adminOnly: true },
  { key: 'notes', label: 'الملاحظات', tone: 'secondary', adminOnly: true },
  { key: 'adminWeekPilot', label: 'اختيار طيار الأسبوع', tone: 'secondary', adminOnly: true },
  { key: 'attendance', label: 'الحضور', tone: 'secondary', adminOnly: true },
]

const TONE_CLASS = {
  primary: 'min-h-[48px] w-full border border-taxi text-[15px] text-taxi',
  secondary: 'min-h-[48px] w-full border border-concrete/45 text-[15px] text-paint',
}

export default function NavBar({ isAdmin, onNavigate }) {
  return (
    <nav className="mt-4 flex flex-col gap-2">
      {NAV_ITEMS.filter((item) => !item.adminOnly || isAdmin).map((item) => (
        <button
          key={item.key}
          type="button"
          onClick={() => onNavigate(item.key)}
          className={TONE_CLASS[item.tone]}
        >
          {item.label}
        </button>
      ))}
    </nav>
  )
}
