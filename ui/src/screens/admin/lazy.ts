/**
 * تسخينُ جزء المشرف **على النيّة** لا على النقر.
 *
 * التقسيم يوفّر على الطالب تنزيل كود المشرف، لكنه يضع على المشرف انتظارًا
 * عند أوّل فتح. فيُبدَأ التنزيل عند أوّل إشارة نيّة (تحويم أو تركيز على
 * المدخل)، ومرّةً على السكون لمن دورُه مشرف — فالطالب لا ينزّله أبدًا،
 * والمشرف عمليًّا لا ينتظره.
 *
 * **ومسار الاستيراد هو نفسه** الذي يستعمله `App.tsx` حرفيًّا؛ مسارٌ مغاير
 * يُنشئ جزءًا ثانيًا فيُنزَّل الكود مرّتين — تسخينٌ يضرّ لا ينفع.
 */
let started = false

export function preloadAdmin(): void {
  if (started) return
  started = true
  void import('./AdminShell')
}

/** يُنادى مرّةً على السكون — لا يزاحم أوّل رسم. */
export function preloadAdminWhenIdle(): void {
  const idle = window.requestIdleCallback
  if (typeof idle === 'function') idle(() => preloadAdmin())
  else window.setTimeout(preloadAdmin, 2000)
}
