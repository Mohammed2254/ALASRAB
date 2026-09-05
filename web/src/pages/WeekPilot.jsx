import Placard from '../components/Placard'
import { Async } from '../components/States'
import { api } from '../lib/api'
import { useAsync } from '../state/useAsync'

/*
  طيار الأسبوع — و-٩د · FR-062.

  **السبب هو المحتوى** (ط-١٠ الحرفي: «القيمة كلّها في لماذا لا في الاسم») —
  يُعرض بارزًا لا كتذييل صغير.
*/

export default function WeekPilot({ onDone }) {
  const state = useAsync(() => api.weekPilot(), [])

  return (
    <div className="taxi-in mx-auto w-full max-w-[520px] px-4 pt-6 pb-10">
      <header className="mb-5 flex items-baseline gap-3">
        <h1 className="font-display text-[26px] leading-none">طيار الأسبوع</h1>
        <span className="centerline" />
        <button
          type="button"
          onClick={onDone}
          className="min-h-[44px] shrink-0 px-2 text-[13px] text-muted"
        >
          رجوع
        </button>
      </header>

      <Async state={state} loadingTitle="طيار الأسبوع">
        {(data) =>
          data.pilot ? (
            <Placard title={data.pilot.full_name} aside="طيار الأسبوع">
              <p className="py-2 text-[14px] text-paint">{data.pilot.reason}</p>
            </Placard>
          ) : (
            <Placard title="طيار الأسبوع">
              <p className="py-2 text-[14px] text-muted">لم يُختَر بعد هذا الأسبوع.</p>
            </Placard>
          )
        }
      </Async>
    </div>
  )
}
