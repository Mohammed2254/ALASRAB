import type { IssuedStudent } from '../../api/types/roster'
import Button from '../../ui/Button'
import Placard from '../../ui/Placard'
import Prow from '../../ui/Prow'

/**
 * بطاقة الرموز الصادرة — **الفرصة الوحيدة لقراءتها**.
 *
 * ولذلك لا تُغلق بنفسها ولا يمحوها تحديثٌ تلقائيّ: المشرف يُغلقها بيده بعد
 * أن ينسخها. وكلّ صفٍّ يحمل رقم الطالب معه، فالورقة تُسلَّم كما هي.
 */
export default function IssuedPins({ issued, onDone }: { issued: IssuedStudent[]; onDone: () => void }) {
  return (
    <Placard title="الرموز الصادرة" aside={`${issued.length}`}>
      <p className="mb-3 text-[13px] text-(--color-accent)">
        انسخ هذه الرموز الآن — لا تُعرض مرّة أخرى. وإن فُقد رمزٌ، أعِد تعيينه من السجلّ.
      </p>
      {issued.map((s) => (
        <Prow
          key={s.id}
          label={s.full_name}
          value={
            <span>
              <bdi dir="ltr">{s.student_no}</bdi>
              {' · '}
              <bdi dir="ltr" className="font-bold text-(--color-text)">
                {s.pin}
              </bdi>
            </span>
          }
        />
      ))}
      <Button variant="outline" onClick={onDone} className="mt-3 w-full">
        نسختُها — إغلاق
      </Button>
    </Placard>
  )
}
