import '@testing-library/jest-dom/vitest'

// jsdom لا يُنفّذ `scrollTo` (`Not implemented`) — و`nav/history.ts::go()`
// يستدعيه في كل انتقال. بلا هذا، كل اختبار تنقّل يُغرق مخرَجه بتحذيرات لا
// علاقة لها بما يُختبَر.
window.scrollTo = () => {}

// jsdom لا يُنفّذ `matchMedia` إطلاقًا — و`motion/mo.ts::reducedMotion()`
// يستدعيه في كل فحص حركة. الافتراض هنا «لا تقليل حركة»؛ الاختبارات التي
// تحتاج عكسه (ق-٢٣٠) تستبدله محليًّا بـ`vi.spyOn`.
window.matchMedia ??= (query: string) =>
  ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }) as MediaQueryList
