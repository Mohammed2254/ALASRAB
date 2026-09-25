import { useSyncExternalStore } from 'react'

import { getMessage, subscribe } from './toastStore'

/** إشعارٌ سفليّ — تُركَّب مرّة واحدة في `App.tsx`، وتُطلَق بـ`toastStore.show()`. */
export default function Toast() {
  const message = useSyncExternalStore(subscribe, getMessage, getMessage)
  return (
    <div
      role="status"
      className={`fixed bottom-6 left-1/2 z-50 max-w-[80%] -translate-x-1/2 rounded-full border border-(--color-border-strong) bg-(--color-surface-2) px-5 py-3 text-center text-[13px] text-(--color-text) transition-opacity duration-300 ${
        message ? 'opacity-100' : 'pointer-events-none opacity-0'
      }`}
    >
      {message}
    </div>
  )
}
