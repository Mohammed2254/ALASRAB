/** زرّ رجوع فرعيّ أعلى شاشات الطيّار الداخلية. */
export default function Subback({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="mb-2.5 flex min-h-[44px] items-center gap-1 border-none bg-transparent p-0 text-[12px] text-(--color-text-dim)"
    >
      ‹ {label}
    </button>
  )
}
