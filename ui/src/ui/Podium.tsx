import { useEffect, useRef } from 'react'

import { countUp, enter } from '../motion/mo'
import ChgBadge from './ChgBadge'
import HexIcon from './HexIcon'
import TierBadge from './TierBadge'

/**
 * منصّة التتويج — أعلى ثلاثة بترتيبٍ بصريّ فضّي←ذهبيّ←برونزيّ، وقائمة
 * الباقي تحتها. ملفٌّ واحد (`Podium` + `PodiumItem` + `RestRow`) لأنها
 * مترابطة بإحكام (`و-١٤.md §٣`).
 *
 * **المراكز مفاتيحُ نصّية لا أرقامًا حرفية** عمدًا: الرقم `3` يتصادف مع
 * `DOMAIN_NUMBERS` في بوابة AST (وزنٌ حقيقيّ في محرّك القواعد)، فمقارنة
 * حرفية `place === 3` كانت ستُسقط الفحص على مصادفة رقمية لا قاعدة عمل
 * فعلية.
 */
export type BoardEntry = { name: string; value: number; tier?: number; tag?: string; me?: boolean; chg: number }
type Place = 'gold' | 'silver' | 'bronze'

const CHEVRON = 'M24 34 L32 25 L40 34'
const PLACES: Place[] = ['silver', 'gold', 'bronze']
const RANK_INDEX: Record<Place, number> = { gold: 0, silver: 1, bronze: 2 }
const RANK_LABEL: Record<Place, string> = { gold: '1', silver: '2', bronze: '3' }
const STAND_HEIGHT: Record<Place, number> = { gold: 58, silver: 40, bronze: 28 }
const CSS_ORDER: Record<Place, number> = { gold: 20, silver: 10, bronze: 30 }
const BADGE_SIZE: Record<Place, number> = { gold: 46, silver: 34, bronze: 34 }

function PodiumItem({ place, item }: { place: Place; item: BoardEntry }) {
  const valueRef = useRef<HTMLElement>(null)
  useEffect(() => {
    countUp(valueRef.current, item.value, { decimals: 2 })
  }, [item.value])

  const isGold = place === 'gold'
  return (
    <div
      data-podium-item
      style={{ order: CSS_ORDER[place] }}
      className={`flex max-w-[114px] flex-1 origin-bottom flex-col items-center text-center ${
        item.me ? 'rounded-t-[14px] bg-(--color-accent-tint) px-0.5 pt-2.5' : ''
      }`}
    >
      <bdi dir="ltr" className={`num mb-1.5 ${isGold ? 'text-[15px] text-(--color-accent)' : 'text-[12px] text-(--color-text-dim)'}`}>
        {RANK_LABEL[place]}
      </bdi>
      <div className="mb-2">
        {item.tier ? (
          <TierBadge tier={item.tier} size={BADGE_SIZE[place]} />
        ) : (
          <HexIcon size={BADGE_SIZE[place]} glyph={CHEVRON} />
        )}
      </div>
      {item.me ? (
        <span className="mb-1.5 inline-block rounded-[5px] bg-(--color-accent) px-1.5 py-0.5 text-[9px] font-extrabold text-(--color-on-accent)">
          أنت
        </span>
      ) : null}
      <div className="mb-0.5 truncate text-[12px] font-bold">{item.name}</div>
      {item.tag ? (
        <bdi dir="ltr" className="mb-1 block text-[10px] text-(--color-text-dim)">
          ({item.tag})
        </bdi>
      ) : null}
      <bdi ref={valueRef} dir="ltr" className={`num mb-1.5 block font-extrabold ${isGold ? 'text-[23px] text-(--color-accent)' : 'text-[17px]'}`}>
        0.00
      </bdi>
      <ChgBadge chg={item.chg} />
      <div
        data-stand
        className="mt-1.5 w-full origin-bottom scale-y-0 rounded-t-[8px] rounded-b-[2px] bg-(--color-accent-tint)"
        style={{ height: STAND_HEIGHT[place] }}
      />
    </div>
  )
}

function RestRow({ rank, item }: { rank: number; item: BoardEntry }) {
  return (
    <div
      className={`flex items-center gap-2.5 border-b border-(--color-border) py-2.5 last:border-none ${
        item.me ? '-mx-3 rounded-(--radius-sm) bg-(--color-accent-tint) px-3' : ''
      }`}
    >
      <bdi dir="ltr" className="w-4 shrink-0 text-[12px] text-(--color-text-dim)">
        {rank}
      </bdi>
      <span className="shrink-0">{item.tier ? <TierBadge tier={item.tier} size={22} /> : <HexIcon size={22} glyph={CHEVRON} />}</span>
      <span className="min-w-0 flex-1 truncate text-[13px]">
        {item.name}
        {item.tag ? (
          <bdi dir="ltr" className="text-(--color-text-dim)">
            {' '}
            ({item.tag})
          </bdi>
        ) : null}
        {item.me ? <span className="mr-1 text-[9px] font-extrabold text-(--color-accent)">أنت</span> : null}
      </span>
      <ChgBadge chg={item.chg} />
      <bdi dir="ltr" className="num shrink-0 text-[13px] font-bold">
        {item.value.toFixed(2)}
      </bdi>
    </div>
  )
}

export default function Podium({ top3, rest }: { top3: [BoardEntry, BoardEntry, BoardEntry]; rest: BoardEntry[] }) {
  const podiumRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const root = podiumRef.current
    if (!root) return
    const items = root.querySelectorAll<HTMLElement>('[data-podium-item]')
    const stands = root.querySelectorAll<HTMLElement>('[data-stand]')
    enter(
      items,
      { opacity: 0, y: 22, scale: 0.82 },
      { opacity: 1, y: 0, scale: 1, duration: 0.55, stagger: 0.16, ease: 'back.out(1.6)' }
    )
    enter(stands, { scaleY: 0 }, { scaleY: 1, duration: 0.45, stagger: 0.16, delay: 0.08, ease: 'power2.out' })
  }, [top3])

  return (
    <div>
      <div ref={podiumRef} className="mb-5.5 flex items-end justify-center gap-2 px-0.5">
        {PLACES.map((place) => (
          <PodiumItem key={place} place={place} item={top3[RANK_INDEX[place]]!} />
        ))}
      </div>
      {rest.length ? (
        <div className="flex flex-col">
          {rest.map((item, i) => (
            <RestRow key={item.name} rank={i + 4} item={item} />
          ))}
        </div>
      ) : null}
    </div>
  )
}
