import { useState } from 'react'

import type { QueueItem } from '../../api/types/adminQueue'
import Button from '../../ui/Button'
import { fieldClass } from '../../ui/Field'
import Placard from '../../ui/Placard'
import Prow from '../../ui/Prow'

/**
 * بطاقةُ طلبٍ في طابور المراجعة — **مشتركةٌ بين `ReadingQueue` و`TahdirQueue`**.
 *
 * استُخرجت في و-٢٢: كانت **منسوخةً حرفيًّا** في الملفّين (نحو سبعين سطرًا)،
 * ولا تختلف النسختان إلا في بادئة `id` — وهي ما يجعل النسخَ غيرَ مرئيّ:
 * الملفّان لا يتجاوران، فمن يُعدّل واحدًا لا يرى الثاني. وفيها **زرّان من
 * أصل خمسةٍ مكرَّرة** في كل شاشات المشرف.
 *
 * **ولم تُرفَع إلى `ui/`:** `QueueItem` نوعٌ من نطاق المراجعة، وبدائياتُ
 * `ui/` لا تعرف نطاقًا (`ARCHITECTURE.md §٢`). فموضعُها بين شاشتَيها.
 *
 * **و`idPrefix` إلزاميّ لا افتراضيّ:** `htmlFor` يربط التسمية بالمُدخَل،
 * وبادئتان متساويتان في صفحةٍ واحدة تجعلان النقرَ على تسميةٍ يُركّز مُدخَلًا
 * آخر — عطلُ وصولٍ لا يراه فحصٌ بصريّ. فالإلزامُ يُجبر المستدعيَ على الاختيار.
 */
export default function QueueItemCard({
  item,
  checked,
  onToggle,
  onReject,
  busy,
  idPrefix,
  formatDay,
}: {
  item: QueueItem
  checked: boolean
  onToggle: () => void
  onReject: (reason: string) => void
  busy: boolean
  idPrefix: string
  formatDay: (iso: string) => string
}) {
  const [rejecting, setRejecting] = useState(false)
  const [reason, setReason] = useState('')
  const reasonId = `${idPrefix}-${item.id}`

  return (
    <Placard title={item.student_name} aside={formatDay(item.read_on)}>
      <Prow label="الكتاب" value={item.book_title} />
      <Prow label="الصفحات" value={<bdi dir="ltr">{item.pages}</bdi>} />

      <div className="mt-3 flex gap-2 border-t border-(--color-border) pt-3">
        <button
          type="button"
          onClick={onToggle}
          className={`min-h-[44px] flex-1 rounded-(--radius-sm) border text-[14px] ${
            checked
              ? 'border-(--color-accent) bg-(--color-accent) text-(--color-on-accent)'
              : 'border-(--color-border-strong) text-(--color-text)'
          }`}
        >
          {checked ? 'محدَّد ✓' : 'تحديد للاعتماد'}
        </button>
        <button
          type="button"
          onClick={() => setRejecting((v) => !v)}
          className="min-h-[44px] min-w-[88px] rounded-(--radius-sm) border border-(--color-border-strong) px-3 text-[14px] text-(--color-text-dim)"
        >
          رفض
        </button>
      </div>

      {rejecting ? (
        <div className="mt-3">
          <label htmlFor={reasonId} className="mb-1.5 block text-[13px] text-(--color-text-dim)">
            سبب الرفض — يراه الطالب
          </label>
          <input
            id={reasonId}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className={fieldClass}
          />
          <Button
            variant="danger"
            disabled={busy || !reason.trim()}
            onClick={() => onReject(reason)}
            className="mt-2 w-full"
          >
            تأكيد الرفض
          </Button>
        </div>
      ) : null}
    </Placard>
  )
}
