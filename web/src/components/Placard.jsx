/*
  اللوح: الحاوية الوحيدة في هذا العالم، ولا لوح داخل لوح أبدًا.
  عنوانه صفّ واحد يقطعه خطّ وسط أصفر متقطّع — الخطّ الذي يقود الطائرة على
  الممرّ يقود العين على طول الصفّ.
*/
export default function Placard({ title, aside, children, className = '' }) {
  return (
    <section className={`placard ${className}`}>
      {title && (
        <header className="flex items-baseline gap-3 border-b border-concrete/35 px-4 py-2.5">
          <span className="threshold shrink-0" aria-hidden="true">
            <span />
            <span />
          </span>
          <h2 className="text-[13px] text-muted">{title}</h2>
          <span className="centerline" />
          {aside && <span className="shrink-0 text-[11px] text-muted">{aside}</span>}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  )
}

/** صفّ بيانات: التسمية ثم خطّ الوسط ثم القيمة — إيقاع لوحة الإقلاع نفسه */
export function Row({ label, value, tone = 'default' }) {
  const tones = { default: 'text-paint', hold: 'text-hold', taxi: 'text-taxi', muted: 'text-muted' }
  return (
    <div className="flex items-baseline gap-3 py-[7px]">
      <span className="shrink-0 text-[13px] text-muted">{label}</span>
      <span className="centerline" style={{ opacity: 0.22 }} />
      <span className={`shrink-0 text-[14px] ${tones[tone]}`}>{value}</span>
    </div>
  )
}
