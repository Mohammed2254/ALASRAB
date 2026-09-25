/**
 * متجر الإشعار — نفس نمط `nav/history.ts`: مصدر حقيقة واحد خارج React،
 * و`useSyncExternalStore` يربطه بـ`<Toast/>`. إشعارٌ واحد في كل لحظة —
 * لا قائمة انتظار، مطابقةً للنموذج المعتمد.
 */
type Listener = () => void

const listeners = new Set<Listener>()
let message: string | null = null
let hideTimer: ReturnType<typeof setTimeout> | undefined

const emit = () => listeners.forEach((fn) => fn())

export const getMessage = (): string | null => message

export function subscribe(listener: Listener): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function show(text: string, durationMs = 2200): void {
  message = text
  emit()
  clearTimeout(hideTimer)
  hideTimer = setTimeout(() => {
    message = null
    emit()
  }, durationMs)
}
