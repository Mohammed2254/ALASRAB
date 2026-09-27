/**
 * تنقّل المشرف — **المصدر الوحيد** لمساره وترتيبه وتسمياته.
 *
 * ترتيب المجموعات وتسمياتها منقولةٌ **حرفيًّا** من `ADMIN_NAV` في النموذج
 * المعتمد، لأن النموذج هو مرجع المنتج النهائيّ (و-٢٠). وسببُ وجود هذا الملفّ
 * أنّ و-١٧ بنى التنقّل الإداريّ على `web/` المرجعيّ القديم — الذي لا يحمل
 * قشرة إدارية أصلًا — فصار المرجع نسخةً متروكة بدل النموذج نفسه.
 *
 * **والعناصر بلا أيقونات عمدًا:** `.side-item` في النموذج تسميةٌ وحدها
 * (`<button class="side-item">label</button>`)، فأيقونةٌ تُضاف هنا زخرفةٌ لم
 * يطلبها التصميم.
 *
 * إضافة شاشة إدارية = سطرٌ في `ADMIN_PATHS` + سطرٌ في `ADMIN_NAV` + سطرٌ في
 * `screens/admin/registry.ts`، و**كلٌّ منها يفشل البناء إن نُسي**: `AdminKey`
 * يُلزم مفتاحَ عنصر القائمة، و`Record<AdminKey, …>` يُلزم السجلّ، واختبار
 * `adminNav.test.ts` يُلزم تغطية القائمة لكل مسارٍ مرّةً واحدة.
 */

/**
 * مسارات المشرف. مفصولةٌ عن `ROUTES` لا مكرَّرة — `routes.ts` يركّبها
 * (`{...PILOT_PATHS, ...ADMIN_PATHS}`)، فيبقى `ScreenKey` سطحًا واحدًا.
 */
export const ADMIN_PATHS = {
  adminDashboard: '/admin',
  adminQueue: '/admin/queue',
  adminTahdirQueue: '/admin/tahdir',
  adminNotes: '/admin/notes',
  adminReport: '/admin/report',
  adminTahdirReport: '/admin/tahdir/report',
  adminAudit: '/admin/audit',
  adminTeams: '/admin/teams',
  adminWeights: '/admin/weights',
  adminThresholds: '/admin/thresholds',
  adminWeekPilot: '/admin/week-pilot',
  adminAttendance: '/admin/attendance',
  adminFuelActivities: '/admin/fuel/activities',
  adminFuelAssess: '/admin/fuel/assess',
  adminQuranEdit: '/admin/quran',
  adminRasdImport: '/admin/rasd',
} as const

export type AdminKey = keyof typeof ADMIN_PATHS

export type AdminNavItem = { key: AdminKey; label: string }

/** `label: null` = مجموعةٌ بلا عنوان (صدر القائمة في النموذج). */
export type AdminNavGroup = { label: string | null; items: readonly AdminNavItem[] }

/**
 * المجموعات الخمس بترتيب النموذج وتسمياته حرفيًّا.
 *
 * و`adminDashboard` في صدر القائمة بلا عنوان مجموعة — كما في النموذج. كان
 * قد سقط في و-١٧ بحجّة «لا مسار خلفيّ يقابله»، وهو تجميعٌ لمسارات قائمة لا
 * نقطةٌ جديدة.
 */
export const ADMIN_NAV: readonly AdminNavGroup[] = [
  { label: null, items: [{ key: 'adminDashboard', label: 'لوحة القيادة' }] },
  {
    label: 'المراجعة',
    items: [
      { key: 'adminQueue', label: 'طابور القراءات' },
      { key: 'adminTahdirQueue', label: 'طابور تحضير القراءة' },
      { key: 'adminNotes', label: 'الملاحظات' },
    ],
  },
  {
    label: 'التقارير',
    items: [
      { key: 'adminReport', label: 'التقرير الدوري' },
      { key: 'adminTahdirReport', label: 'تقرير تحضير القراءة' },
      { key: 'adminAudit', label: 'الصندوق الأسود' },
    ],
  },
  {
    label: 'الإدارة',
    items: [
      { key: 'adminTeams', label: 'الأسراب' },
      { key: 'adminWeights', label: 'الأوزان' },
      { key: 'adminThresholds', label: 'العتبات' },
      { key: 'adminWeekPilot', label: 'اختيار طيّار الأسبوع' },
      { key: 'adminAttendance', label: 'الحضور' },
    ],
  },
  {
    label: 'الوقود',
    items: [
      { key: 'adminFuelActivities', label: 'أنشطة الوقود' },
      { key: 'adminFuelAssess', label: 'تقييم نشاط' },
    ],
  },
  {
    label: 'القرآن',
    items: [
      { key: 'adminQuranEdit', label: 'التصحيح والتعديل القرآني' },
      { key: 'adminRasdImport', label: 'استيراد راصد' },
    ],
  },
]

// مجموعةٌ تُبنى مرّةً واحدة: السؤال يقع في كل تنقّل، و`Object.keys` في كلّ
// مرّة يجعل ثمنَ الإجابة بعددِ الشاشات بلا سبب.
const ADMIN_KEYS: ReadonlySet<string> = new Set(Object.keys(ADMIN_PATHS))

/** هل الشاشة إدارية؟ — السؤال الوحيد الذي تسأله القشرة قبل رسم لوحة المشرف. */
export const isAdminScreen = (key: string): key is AdminKey => ADMIN_KEYS.has(key)

/**
 * مفتاحٌ ⇒ تسميته المعروضة، مشتقّةٌ من `ADMIN_NAV` لا مكتوبةً ثانيةً —
 * فالعنوان في القشرة هو نفسه العنوان في القائمة بالبناء لا بالانتباه.
 * (الاستيفاء يحرسه `adminNav.test.ts`، فالتأكيد هنا ليس ادّعاءً بلا فحص.)
 */
export const LABEL_OF = Object.fromEntries(
  ADMIN_NAV.flatMap((group) => group.items.map((item) => [item.key, item.label]))
) as Readonly<Record<AdminKey, string>>
