/**
 * جدول الشاشات ومساراتها — ADR-008.
 *
 * **مفتاحٌ واحد لكل شاشة، ومسارٌ واحد لكل مفتاح.** والجدول هو المصدر الوحيد
 * للاثنين، فإضافة شاشة سطرٌ واحد هنا لا ثلاثة مواضع.
 *
 * والمسارات حقيقية لا زينة: الروابط تُشارَك وتُحفَظ، وزرّ الرجوع في أندرويد
 * يعمل — وهو ما كان مكسورًا في البناء الأول بسجلّ الشاشات.
 *
 * **ومسارات المشرف تُركَّب من `adminNav.ts` لا تُكرَّر هنا** (و-٢٠): ذاك
 * الملفّ يقود القائمة الجانبية وسجلّ الشاشات معًا، فجدولٌ ثانٍ بالمسارات
 * نفسها يصير نسخةً ثالثة تتباعد عن الاثنتين. والسطح العامّ لم يتغيّر —
 * `ScreenKey` و`keyOf` و`pathOf` كما كانت.
 */
import { ADMIN_PATHS } from './adminNav'

const PILOT_PATHS = {
  deck: '/',
  readings: '/readings',
  tahdir: '/tahdir',
  station: '/station',
  formation: '/formation',
  board: '/board',
  question: '/question',
  weekPilot: '/week-pilot',
  note: '/note',
} as const

// الأنواع الحرفية تنجو من النشر لأن المصدرين `as const` كلاهما.
export const ROUTES = { ...PILOT_PATHS, ...ADMIN_PATHS } as const

export type ScreenKey = keyof typeof ROUTES

/** الشاشة الجذر — الرجوع منها يخرج من التطبيق، وهذا سلوكٌ صحيح لا فخّ. */
export const ROOT_KEY: ScreenKey = 'deck'

// عكسُ الجدول يُبنى مرّةً واحدة: المطابقة بالمسار تقع في كل `popstate`.
const BY_PATH = new Map<string, ScreenKey>(
  Object.entries(ROUTES).map(([key, path]) => [path, key as ScreenKey])
)

/**
 * مسارٌ ⇒ مفتاح. والمسار المجهول يعطي الجذر — رابطٌ قديم أو مكسور يهبط
 * بالطالب على بطاقته لا على شاشة خطأ.
 */
export function keyOf(pathname: string): ScreenKey {
  const clean = pathname.replace(/\/+$/, '') || '/'
  return BY_PATH.get(clean) ?? ROOT_KEY
}

/** مفتاحٌ ⇒ مسار. */
export const pathOf = (key: ScreenKey): string => ROUTES[key]
