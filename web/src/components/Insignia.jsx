/*
  شارات الرتب.

  شرط الجمعية أنها ستُطبع شارات قماشية مخيطة، فكل علامة هنا:
    · بلون واحد مصمت — بلا تدرّج ولا شفافية ولا ظلّ،
    · مميّزة بالصورة الظلّية وحدها: لو طُبعت كلّها بخيط واحد لبقيت متمايزة،
    · بلا تفصيل أدقّ من سُدس عرضها، فلا يضيع في الخياطة.

  التدوين مأخوذ من رتب الطيران الحقيقية: شيفرون ← أجنحة ← نجمة. لا سيف ولا سهم
  ولا أي رمز اشتباك (قيد المحتوى في `SCOPE.md` §١٣).

  **الترتيب تصاعدي، وسلسلة العلامات أطول من السُّلّم عمدًا.** السُّلّم أربع رتب
  اليوم وسيزيد (`SCOPE.md` §٤)، وإضافة رتبة **صفٌّ في `rank_thresholds`** — فيجب
  ألّا تحتاج إعادة رسم السلسلة كلها (`VISUAL.md` §٦). والزائد عن العلامات يأخذ
  أعلاها بدل أن يختفي.

  thread = خيط الحدّ المضفور، وهو لون السرب: انتماءٌ بصريّ بلا لون توكيد ثانٍ
  يكسر نظام علامات المطار.
*/
const CHEVRON = 'M8 30 L24 17 L40 30 L40 37 L24 24 L8 37 Z'
const WINGS =
  'M24 21.5 a2.8 2.8 0 1 1 0 5.6 a2.8 2.8 0 1 1 0 -5.6 ' +
  'M27.4 22.4 L46 25.4 L46 28.4 L27.4 27.4 Z ' +
  'M20.6 22.4 L2 25.4 L2 28.4 L20.6 27.4 Z'
const STAR =
  'M24 3 L26 9.4 L32.6 9.4 L27.3 13.4 L29.3 19.8 L24 15.8 L18.7 19.8 L20.7 13.4 L15.4 9.4 L22 9.4 Z'

const bars = (n) =>
  Array.from({ length: n }, (_, i) => <rect key={i} x="14" y={34 + i * 5} width="20" height="3" />)

/** من الأدنى إلى الأعلى. الفهرس = tier − 1. */
const MARKS = [
  () => <path d={CHEVRON} />,
  () => (
    <>
      <path d={CHEVRON} />
      <path d={CHEVRON} transform="translate(0,11)" />
    </>
  ),
  () => (
    <>
      <path d={WINGS} />
      {bars(1)}
    </>
  ),
  () => (
    <>
      <path d={WINGS} />
      {bars(2)}
    </>
  ),
  () => (
    <>
      <path d={STAR} />
      <path d={WINGS} transform="translate(0,4)" />
      {bars(3)}
    </>
  ),
]

export default function Insignia({ tier, size = 44, thread, patch = true, title }) {
  // القصّ لا الطيّ: رتبة تاسعة يجب أن تُعرض بأعلى علامة، لا أن تعود إلى الشيفرون.
  const Mark = MARKS[Math.min(Math.max(tier ?? 1, 1), MARKS.length) - 1]
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      className="shrink-0"
      role={title ? 'img' : undefined}
      aria-label={title}
      aria-hidden={title ? undefined : 'true'}
    >
      {patch && (
        <rect
          x="1.5"
          y="1.5"
          width="45"
          height="45"
          rx="9"
          fill="var(--color-taxiway)"
          stroke={thread ?? 'var(--color-taxi)'}
          strokeWidth="3"
        />
      )}
      <g fill="var(--color-paint)">
        <Mark />
      </g>
    </svg>
  )
}
