import '@testing-library/jest-dom/vitest'

// jsdom لا يُنفّذ `scrollTo` (`Not implemented`) — و`nav/history.ts::go()`
// يستدعيه في كل انتقال. بلا هذا، كل اختبار تنقّل يُغرق مخرَجه بتحذيرات لا
// علاقة لها بما يُختبَر.
window.scrollTo = () => {}
