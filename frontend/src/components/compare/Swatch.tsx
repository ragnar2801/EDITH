/** A short line in a series' colour, as in the chart's legend. */
export function Swatch({ color, dashed = false }: { color: string; dashed?: boolean }) {
  return (
    <svg width="14" height="4" aria-hidden className="shrink-0">
      <line
        x1="0"
        x2="14"
        y1="2"
        y2="2"
        stroke={color}
        strokeWidth="3"
        strokeDasharray={dashed ? '4 3' : undefined}
      />
    </svg>
  )
}
