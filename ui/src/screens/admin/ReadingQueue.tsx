import { useState } from 'react'

import { api } from '../../api'
import type { QueueItem } from '../../api/types/adminQueue'
import { useAsync } from '../../state/useAsync'
import { useSubmit } from '../../state/useSubmit'
import { Async } from '../../ui/Async'
import Button from '../../ui/Button'
import EmptyState from '../../ui/EmptyState'
import Placard from '../../ui/Placard'
import QueueItemCard from './QueueItemCard'
import ErrorText from '../../ui/ErrorText'

/**
 * طابور اعتماد القراءات — `GET/POST /admin/readings*` (FR-022..024).
 * **الاعتماد الجماعي ليس رفاهية**: الاعتماد الفردي في طابور من عشرين طلبًا
 * يخالف NFR-02. ولا حساب هنا — الساعات تعود من الخادم بعد الاعتماد.
 */

const dayFormatter = new Intl.DateTimeFormat('ar-SA-u-ca-gregory-nu-latn', {
  day: 'numeric',
  month: 'long',
  timeZone: 'Asia/Riyadh',
})
const formatDay = (iso: string) => dayFormatter.format(new Date(`${iso}T00:00:00Z`))


function Queue({ submissions, onChanged }: { submissions: QueueItem[]; onChanged: () => void }) {
  const [selected, setSelected] = useState<number[]>([])
  const { busy, error, run } = useSubmit()

  // النجاحُ يُفرّغ التحديد ويُعيد التحميل — و`run` يُرجع `true` عنده، فالقرارُ
  // هنا لا داخل الخطّاف: شاشةٌ أخرى قد تريد إبقاءَ التحديد.
  const review = async (action: () => Promise<unknown>) => {
    if (await run(async () => void (await action()))) {
      setSelected([])
      onChanged()
    }
  }

  if (submissions.length === 0) {
    return (
      <Placard title="الطابور">
        <EmptyState>لا طلبات تنتظر المراجعة.</EmptyState>
      </Placard>
    )
  }

  const toggle = (id: number) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]))


  return (
    <div className="flex flex-col gap-3.5">
      {selected.length ? (
        <Button disabled={busy} onClick={() => review(() => api.admin.approveReadings(selected))} className="w-full">
          {busy ? 'جارٍ الاعتماد…' : `اعتماد المحدَّد (${selected.length})`}
        </Button>
      ) : null}

      {error ? <ErrorText spacing="">{error}</ErrorText> : null}

      {submissions.map((s) => (
        <QueueItemCard
          key={s.id}
          item={s}
          checked={selected.includes(s.id)}
          onToggle={() => toggle(s.id)}
          onReject={(reason) => review(() => api.admin.rejectReading(s.id, reason))}
          busy={busy}
          idPrefix="reason"
          formatDay={formatDay}
        />
      ))}
    </div>
  )
}

export default function ReadingQueue() {
  const state = useAsync(() => api.admin.readingQueue(), [])

  return (
    <div className="flex flex-col gap-3.5">
      <Async state={state} loadingTitle="الطابور">
        {(data) => <Queue submissions={data.submissions} onChanged={state.reload} />}
      </Async>
    </div>
  )
}
