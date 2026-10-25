import { useEffect, useMemo, useRef, useState, type PointerEvent } from 'react'

import { formatDate, formatMonthYear } from '@/lib/time'

export type ChartPoint = { date: string; value: string }
export type ChartSeries = {
  name: string
  /** A CSS colour, e.g. `var(--chart-main)`. */
  color: string
  points: ChartPoint[]
  dashed?: boolean
}
export type ChartSelection = { start: string; end: string }
export type ChartMarker = { date: string; side: 'buy' | 'sell' }

type Props = {
  label: string
  series: ChartSeries[]
  /** Tooltip text for a value from the API (e.g. `inr`). */
  formatValue: (value: string) => string
  /** Axis tick text. Ticks are drawing positions, not figures from the API. */
  formatAxis: (value: number) => string
  height?: number
  area?: boolean
  selectable?: boolean
  selection?: ChartSelection | null
  onSelectionChange?: (selection: ChartSelection | null) => void
  markers?: ChartMarker[]
}

const DEFAULT_WIDTH = 820
const PAD = { left: 60, right: 14, top: 14, bottom: 24 }

/**
 * Line chart in plain SVG (D-050), ported from Friday: hover read-out, drag to select an
 * interval, buy/sell markers. Values arrive as exact strings; they become numbers only to
 * place points on screen. Every figure shown as text is the API's own string.
 */
export function LineChart({
  label,
  series,
  formatValue,
  formatAxis,
  height = 300,
  area = false,
  selectable = false,
  selection = null,
  onSelectionChange,
  markers = [],
}: Props) {
  const frame = useRef<HTMLDivElement>(null)
  // Draw at the real width, so text stays readable on a phone instead of shrinking.
  const [W, setWidth] = useState(DEFAULT_WIDTH)
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
  const [hover, setHover] = useState(-1)
  const [drag, setDrag] = useState<{ anchor: number; cursor: number } | null>(null)

  const geometry = useMemo(() => {
    const lines = series.filter((line) => line.points.length > 0)
    if (lines.length === 0) return null
    const plotW = W - PAD.left - PAD.right
    const plotH = height - PAD.top - PAD.bottom

    const dates = [...new Set(lines.flatMap((line) => line.points.map((p) => p.date)))].sort()
    const index = new Map(dates.map((date, i) => [date, i]))
    const n = dates.length

    let lo = Infinity
    let hi = -Infinity
    for (const line of lines) {
      for (const point of line.points) {
        const value = Number(point.value)
        if (value < lo) lo = value
        if (value > hi) hi = value
      }
    }
    const pad = (hi - lo) * 0.08 || Math.abs(hi) * 0.1 || 1
    // Money and NAVs never go below zero, so neither does the axis.
    lo = lo >= 0 ? Math.max(0, lo - pad) : lo - pad
    hi += pad

    const x = (i: number) => PAD.left + (n <= 1 ? plotW / 2 : (i / (n - 1)) * plotW)
    const y = (value: number) => PAD.top + (1 - (value - lo) / (hi - lo)) * plotH

    const drawn = lines.map((line) => ({
      ...line,
      byDate: new Map(line.points.map((point) => [point.date, point.value])),
      path: line.points
        .map(
          (point) => `${x(index.get(point.date)!).toFixed(1)},${y(Number(point.value)).toFixed(1)}`,
        )
        .join(' '),
    }))

    let areaPath: string | null = null
    if (area) {
      const first = lines[0].points
      const top = first
        .map((p) => `${x(index.get(p.date)!).toFixed(1)},${y(Number(p.value)).toFixed(1)}`)
        .join(' L ')
      const base = (height - PAD.bottom).toFixed(1)
      const x0 = x(index.get(first[0].date)!).toFixed(1)
      const x1 = x(index.get(first[first.length - 1].date)!).toFixed(1)
      areaPath = `M ${x0},${base} L ${top} L ${x1},${base} Z`
    }

    const yTicks = [0, 0.25, 0.5, 0.75, 1].map((t) => ({
      y: PAD.top + t * plotH,
      label: formatAxis(lo + (hi - lo) * (1 - t)),
    }))
    const xTicks = [...new Set([0, Math.floor((n - 1) / 2), n - 1])].map((i) => ({
      x: x(i),
      label: formatMonthYear(dates[i]),
      anchor: (n > 1 && i === 0 ? 'start' : n > 1 && i === n - 1 ? 'end' : 'middle') as
        'start' | 'end' | 'middle',
    }))
    return { dates, n, x, y, plotW, plotH, lines: drawn, areaPath, yTicks, xTicks }
  }, [series, height, area, formatAxis, W])

  if (!geometry) {
    return (
      <div ref={frame}>
        <p className="text-muted-foreground py-8 text-center text-sm">No data to plot.</p>
      </div>
    )
  }
  const g = geometry

  function indexAt(event: PointerEvent<SVGSVGElement>): number {
    const box = event.currentTarget.getBoundingClientRect()
    const px = ((event.clientX - box.left) * W) / box.width
    const i = Math.round(((px - PAD.left) / g.plotW) * (g.n - 1))
    return Math.max(0, Math.min(g.n - 1, i))
  }

  function finishDrag() {
    if (!drag) return
    setDrag(null)
    const lo = Math.min(drag.anchor, drag.cursor)
    const hi = Math.max(drag.anchor, drag.cursor)
    if (hi - lo < 1) {
      if (selection) onSelectionChange?.(null) // a click clears the selection
      return
    }
    onSelectionChange?.({ start: g.dates[lo], end: g.dates[hi] })
  }

  let band: { x: number; w: number } | null = null
  const span = drag
    ? [Math.min(drag.anchor, drag.cursor), Math.max(drag.anchor, drag.cursor)]
    : selection
      ? [g.dates.indexOf(selection.start), g.dates.indexOf(selection.end)]
      : null
  if (span && span[0] >= 0 && span[1] > span[0]) {
    band = { x: g.x(span[0]), w: g.x(span[1]) - g.x(span[0]) }
  }

  const tip =
    hover >= 0
      ? (() => {
          const date = g.dates[hover]
          const rows = g.lines
            .filter((line) => line.byDate.has(date))
            .map((line) => ({
              name: line.name,
              color: line.color,
              y: g.y(Number(line.byDate.get(date))),
              text: formatValue(line.byDate.get(date)!),
            }))
          const boxW = Math.min(220, W - PAD.left - PAD.right)
          const boxH = 24 + rows.length * 16
          const hx = g.x(hover)
          return {
            date,
            rows,
            boxW,
            boxH,
            x: hx,
            tx: Math.max(0, Math.min(W - boxW, hx + boxW + 14 > W ? hx - boxW - 8 : hx + 8)),
          }
        })()
      : null

  const bottom = height - PAD.bottom
  return (
    <div ref={frame}>
      <figure className="flex flex-col gap-1.5">
        <figcaption className="text-muted-foreground flex flex-wrap gap-x-4 gap-y-1 text-xs">
          {g.lines.map((line) => (
            <span key={line.name} className="inline-flex items-center gap-1.5">
              <svg width="16" height="4" aria-hidden>
                <line
                  x1="0"
                  x2="16"
                  y1="2"
                  y2="2"
                  stroke={line.color}
                  strokeWidth="3"
                  strokeDasharray={line.dashed ? '4 3' : undefined}
                />
              </svg>
              {line.name}
            </span>
          ))}
        </figcaption>
        <svg
          role="img"
          aria-label={label}
          viewBox={`0 0 ${W} ${height}`}
          className={selectable ? 'w-full cursor-crosshair touch-none select-none' : 'w-full'}
          onPointerDown={(event) => {
            if (!selectable) return
            event.currentTarget.setPointerCapture(event.pointerId)
            const i = indexAt(event)
            setDrag({ anchor: i, cursor: i })
          }}
          onPointerMove={(event) => {
            const i = indexAt(event)
            setHover(i)
            if (drag) setDrag({ anchor: drag.anchor, cursor: i })
          }}
          onPointerUp={finishDrag}
          onPointerLeave={() => {
            setHover(-1)
            finishDrag()
          }}
        >
          {g.yTicks.map((tick) => (
            <g key={tick.y}>
              <line
                x1={PAD.left}
                x2={W - PAD.right}
                y1={tick.y}
                y2={tick.y}
                className="stroke-border"
              />
              <text
                x={PAD.left - 8}
                y={tick.y + 3}
                textAnchor="end"
                className="fill-muted-foreground text-[11px]"
              >
                {tick.label}
              </text>
            </g>
          ))}
          {g.xTicks.map((tick) => (
            <text
              key={tick.x}
              x={tick.x}
              y={height - 6}
              textAnchor={tick.anchor}
              className="fill-muted-foreground text-[11px]"
            >
              {tick.label}
            </text>
          ))}
          {band && (
            <rect
              x={band.x}
              y={PAD.top}
              width={band.w}
              height={g.plotH}
              className="fill-chart-main/15 stroke-chart-main/60"
            />
          )}
          {g.areaPath && (
            <path d={g.areaPath} fill={g.lines[0].color} fillOpacity={0.1} stroke="none" />
          )}
          {g.lines.map((line) => (
            <polyline
              key={line.name}
              points={line.path}
              fill="none"
              stroke={line.color}
              strokeWidth={2}
              strokeLinejoin="round"
              strokeLinecap="round"
              strokeDasharray={line.dashed ? '5 4' : undefined}
            />
          ))}
          {markers.map((marker, i) => {
            let at = g.dates.indexOf(marker.date)
            if (at < 0) at = g.dates.findIndex((date) => date >= marker.date)
            if (at < 0) return null
            const mx = g.x(at)
            const buy = marker.side === 'buy'
            const colour = buy ? 'var(--positive)' : 'var(--destructive)'
            const tri = buy
              ? `M ${mx - 4} ${bottom} L ${mx + 4} ${bottom} L ${mx} ${bottom - 8} Z`
              : `M ${mx - 4} ${PAD.top} L ${mx + 4} ${PAD.top} L ${mx} ${PAD.top + 8} Z`
            return (
              <g key={`${marker.date}-${i}`} data-marker={marker.side}>
                <line
                  x1={mx}
                  x2={mx}
                  y1={PAD.top}
                  y2={bottom}
                  stroke={colour}
                  strokeDasharray="2 3"
                  opacity={0.35}
                />
                <path d={tri} fill={colour} />
              </g>
            )
          })}
          {tip && (
            <g>
              <line
                x1={tip.x}
                x2={tip.x}
                y1={PAD.top}
                y2={bottom}
                className="stroke-muted-foreground"
                strokeDasharray="3 3"
              />
              {tip.rows.map((row) => (
                <circle key={row.name} cx={tip.x} cy={row.y} r={3.5} fill={row.color} />
              ))}
              <g transform={`translate(${tip.tx},${PAD.top})`}>
                <rect
                  width={tip.boxW}
                  height={tip.boxH}
                  rx={6}
                  className="fill-popover stroke-border"
                />
                <text x={8} y={16} className="fill-muted-foreground text-[12px]">
                  {formatDate(tip.date)}
                </text>
                {tip.rows.map((row, i) => (
                  <text
                    key={row.name}
                    x={8}
                    y={33 + i * 16}
                    className="fill-foreground text-[12px]"
                  >
                    <tspan fill={row.color}>●</tspan> {row.name}: {row.text}
                  </text>
                ))}
              </g>
            </g>
          )}
        </svg>
      </figure>
    </div>
  )
}
