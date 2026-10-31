import { useEffect, useMemo, useRef, useState } from 'react'

export type ScatterPoint = {
  /** Exact strings from the API; numbers only to place the dot. */
  x: string
  y: string
  /** Shown on hover, built from the API's strings. */
  label: string
  muted?: boolean
}
export type ScatterMark = ScatterPoint & { name: string; color: string }

type Props = {
  label: string
  points: ScatterPoint[]
  /** Points drawn larger and named in the legend, e.g. the model and the benchmark. */
  marks?: ScatterMark[]
  xLabel: string
  yLabel: string
  /** Axis tick text. Ticks are drawing positions, not figures from the API. */
  formatAxis: (value: number) => string
  height?: number
}

const PAD = { left: 52, right: 14, top: 14, bottom: 36 }

function ticks(lo: number, hi: number, count = 5): number[] {
  const span = hi - lo || 1
  const raw = span / count
  const magnitude = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 5, 10].map((m) => m * magnitude).find((s) => s >= raw) ?? raw
  const out = []
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(v)
  return out
}

/** Dots in plain SVG (D-050's way): many points, a few named marks, hover read-out. */
export function ScatterChart({
  label,
  points,
  marks = [],
  xLabel,
  yLabel,
  formatAxis,
  height = 320,
}: Props) {
  const frame = useRef<HTMLDivElement>(null)
  const [W, setWidth] = useState(820)
  useEffect(() => {
    const element = frame.current
    if (!element || typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(([entry]) => {
      const width = Math.round(entry.contentRect.width)
      if (width > 0) setWidth(Math.max(280, width))
    })
    observer.observe(element)
    return () => observer.disconnect()
  }, [])
  const [hover, setHover] = useState<ScatterPoint | null>(null)

  const geometry = useMemo(() => {
    const all = [...points, ...marks].filter((p) => p.x !== '' && p.y !== '')
    if (all.length === 0) return null
    const xs = all.map((p) => Number(p.x))
    const ys = all.map((p) => Number(p.y))
    const pad = (lo: number, hi: number) => {
      const extra = (hi - lo || Math.abs(hi) || 1) * 0.05
      return [lo - extra, hi + extra] as const
    }
    const [x0, x1] = pad(Math.min(...xs), Math.max(...xs))
    const [y0, y1] = pad(Math.min(...ys), Math.max(...ys))
    const plotW = W - PAD.left - PAD.right
    const plotH = height - PAD.top - PAD.bottom
    const sx = (v: number) => PAD.left + ((v - x0) / (x1 - x0)) * plotW
    const sy = (v: number) => PAD.top + (1 - (v - y0) / (y1 - y0)) * plotH
    return { sx, sy, xTicks: ticks(x0, x1), yTicks: ticks(y0, y1), plotW, plotH }
  }, [points, marks, W, height])

  if (!geometry) return null
  const { sx, sy, xTicks, yTicks, plotW, plotH } = geometry
  const place = (p: ScatterPoint) => [sx(Number(p.x)), sy(Number(p.y))] as const

  function nearest(clientX: number, clientY: number, box: DOMRect) {
    const mx = ((clientX - box.left) / box.width) * W
    const my = ((clientY - box.top) / box.height) * height
    let best: ScatterPoint | null = null
    let distance = 14 * 14
    for (const p of [...marks, ...points]) {
      if (p.x === '' || p.y === '') continue
      const [px, py] = place(p)
      const d = (px - mx) ** 2 + (py - my) ** 2
      if (d < distance) [best, distance] = [p, d]
    }
    setHover(best)
  }

  return (
    <div ref={frame} className="flex flex-col gap-2">
      <div className="text-muted-foreground flex min-h-5 flex-wrap items-center gap-x-4 gap-y-1 text-xs">
        {marks.map((mark) => (
          <span key={mark.name} className="flex items-center gap-1.5">
            <span className="size-2.5 rounded-full" style={{ background: mark.color }} />
            {mark.name}
          </span>
        ))}
        <span className="ml-auto tabular-nums" aria-live="polite">
          {hover?.label}
        </span>
      </div>
      <svg
        role="img"
        aria-label={label}
        viewBox={`0 0 ${W} ${height}`}
        className="w-full touch-none select-none"
        onPointerMove={(event) =>
          nearest(event.clientX, event.clientY, event.currentTarget.getBoundingClientRect())
        }
        onPointerLeave={() => setHover(null)}
      >
        {yTicks.map((v) => (
          <g key={`y${v}`}>
            <line
              x1={PAD.left}
              x2={PAD.left + plotW}
              y1={sy(v)}
              y2={sy(v)}
              className="stroke-border"
            />
            <text
              x={PAD.left - 6}
              y={sy(v)}
              textAnchor="end"
              dominantBaseline="middle"
              className="fill-muted-foreground text-[10px]"
            >
              {formatAxis(v)}
            </text>
          </g>
        ))}
        {xTicks.map((v) => (
          <text
            key={`x${v}`}
            x={sx(v)}
            y={PAD.top + plotH + 14}
            textAnchor="middle"
            className="fill-muted-foreground text-[10px]"
          >
            {formatAxis(v)}
          </text>
        ))}
        <text
          x={PAD.left + plotW / 2}
          y={height - 4}
          textAnchor="middle"
          className="fill-muted-foreground text-[11px]"
        >
          {xLabel}
        </text>
        <text
          transform={`translate(12 ${PAD.top + plotH / 2}) rotate(-90)`}
          textAnchor="middle"
          className="fill-muted-foreground text-[11px]"
        >
          {yLabel}
        </text>
        {points.map((p, i) => {
          if (p.x === '' || p.y === '') return null
          const [cx, cy] = place(p)
          return (
            <circle
              key={i}
              cx={cx}
              cy={cy}
              r={2}
              style={{ fill: p.muted ? 'var(--muted-foreground)' : 'var(--chart-main)' }}
              opacity={p.muted ? 0.25 : 0.55}
            />
          )
        })}
        {marks.map((mark) => {
          if (mark.x === '' || mark.y === '') return null
          const [cx, cy] = place(mark)
          return (
            <circle
              key={mark.name}
              cx={cx}
              cy={cy}
              r={5.5}
              style={{ fill: mark.color }}
              className="stroke-background"
              strokeWidth={2}
            />
          )
        })}
        {hover && (
          <circle
            cx={place(hover)[0]}
            cy={place(hover)[1]}
            r={7}
            fill="none"
            className="stroke-foreground"
            strokeWidth={1.5}
          />
        )}
      </svg>
    </div>
  )
}
