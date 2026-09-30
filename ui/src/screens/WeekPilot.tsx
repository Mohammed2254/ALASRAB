import { api } from '../api'
import { go } from '../nav/history'
import { useAsync } from '../state/useAsync'
import { Async } from '../ui/Async'
import CelebrateBadge from '../ui/CelebrateBadge'
import EmptyState from '../ui/EmptyState'
import { GLYPHS } from '../ui/glyphs'
import HexIcon from '../ui/HexIcon'
import Placard from '../ui/Placard'
import Subback from '../ui/Subback'

/**
 * طيار الأسبوع — `GET /week/pilot` (FR-062). **السبب هو المحتوى** — يُعرض
 * بارزًا في متن اللوح لا كتذييل صغير.
 */
export default function WeekPilot() {
  const state = useAsync(() => api.engagement.weekPilot(), [])

  return (
    <div className="flex flex-col gap-3.5">
      <Subback label="الرئيسية" onClick={() => go('deck')} />
      <Async state={state} loadingTitle="طيار الأسبوع">
        {(data) =>
          data.pilot ? (
            <Placard title={data.pilot.full_name} aside="طيار الأسبوع">
              {/* الهالة النابضة — لحظةٌ توقيعية من النموذج. حركةُ CSS محضة،
                  فتخضع مجّانًا لقاعدة تقليل الحركة في `base.css`. */}
              <CelebrateBadge>
                <HexIcon size={56} glyph={GLYPHS.star} filled />
              </CelebrateBadge>
              <p className="py-2 text-center text-[14px] text-(--color-text)">
                {data.pilot.reason}
              </p>
            </Placard>
          ) : (
            <Placard title="طيار الأسبوع">
              <EmptyState>لم يُختَر بعد هذا الأسبوع.</EmptyState>
            </Placard>
          )
        }
      </Async>
    </div>
  )
}
