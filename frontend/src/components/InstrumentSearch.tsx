import { Loader2, Search } from 'lucide-react'
import { useId, useState, type KeyboardEvent } from 'react'

import { useInstrumentSearch } from '@/api/queries'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { useDebouncedValue } from '@/hooks/use-debounced-value'
import {
  ASSET_CLASS_LABELS,
  KIND_LABELS,
  listingLabel,
  planLabel,
  type InstrumentSummary,
} from '@/lib/instruments'
import { cn } from '@/lib/utils'

type Props = {
  onSelect: (instrument: InstrumentSummary) => void
  label?: string
  placeholder?: string
  autoFocus?: boolean
}

/**
 * Find any stock, ETF or mutual fund by part of its name, its symbol, scheme code or ISIN
 * (D-042). Reusable: holdings and the watchlist pick instruments with it.
 */
export function InstrumentSearch({
  onSelect,
  label = 'Search instruments',
  placeholder = 'Name, symbol, scheme code or ISIN',
  autoFocus,
}: Props) {
  const listId = useId()
  const [text, setText] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const query = useDebouncedValue(text.trim(), 200)
  const search = useInstrumentSearch(query)
  const results = query ? (search.data ?? []) : []
  const showList = open && query.length > 0

  function choose(instrument: InstrumentSummary) {
    onSelect(instrument)
    setText('')
    setOpen(false)
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setOpen(true)
      setActive((index) => Math.min(index + 1, results.length - 1))
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActive((index) => Math.max(index - 1, 0))
    } else if (event.key === 'Enter' && showList && results[active]) {
      event.preventDefault()
      choose(results[active])
    } else if (event.key === 'Escape') {
      setOpen(false)
    }
  }

  return (
    <div className="relative">
      <Search
        aria-hidden
        className="text-muted-foreground pointer-events-none absolute top-2.5 left-3 size-4"
      />
      <Input
        role="combobox"
        aria-label={label}
        aria-expanded={showList}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={showList && results[active] ? `${listId}-${active}` : undefined}
        autoComplete="off"
        spellCheck={false}
        autoFocus={autoFocus}
        placeholder={placeholder}
        className="pl-9"
        value={text}
        onChange={(event) => {
          setText(event.target.value)
          setActive(0)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={onKeyDown}
      />
      {search.isFetching && query && (
        <Loader2
          aria-hidden
          className="text-muted-foreground absolute top-2.5 right-3 size-4 animate-spin"
        />
      )}
      {showList && (
        <ul
          id={listId}
          role="listbox"
          aria-label={label}
          className="bg-popover text-popover-foreground absolute z-20 mt-1 max-h-96 w-full overflow-y-auto rounded-md border p-1 shadow-md"
        >
          {results.map((instrument, index) => (
            <li
              key={instrument.id}
              id={`${listId}-${index}`}
              role="option"
              aria-selected={index === active}
              className={cn(
                'flex cursor-pointer flex-col gap-1 rounded-sm px-3 py-2 text-sm',
                index === active && 'bg-accent text-accent-foreground',
              )}
              // mousedown, not click: the input's blur would close the list first
              onMouseDown={(event) => {
                event.preventDefault()
                choose(instrument)
              }}
              onMouseEnter={() => setActive(index)}
            >
              <span className="font-medium">{instrument.name}</span>
              <span className="text-muted-foreground flex flex-wrap items-center gap-1.5 text-xs">
                <span>{listingLabel(instrument)}</span>
                {planLabel(instrument) && <span>· {planLabel(instrument)}</span>}
                <Badge variant="outline">{KIND_LABELS[instrument.kind]}</Badge>
                <Badge variant="outline">{ASSET_CLASS_LABELS[instrument.asset_class]}</Badge>
                <Badge variant="outline">{instrument.currency}</Badge>
                {!instrument.is_active && <Badge variant="secondary">inactive</Badge>}
                {instrument.variants.length > 0 && (
                  <span>
                    · {instrument.variants.length} other plan
                    {instrument.variants.length === 1 ? '' : 's'}
                  </span>
                )}
              </span>
            </li>
          ))}
          {search.isSuccess && !search.isPlaceholderData && results.length === 0 && (
            <li className="text-muted-foreground px-3 py-2 text-sm" role="presentation">
              No matches for “{query}”.
            </li>
          )}
          {search.isError && (
            <li className="text-destructive px-3 py-2 text-sm" role="presentation">
              Search failed: {search.error.message}
            </li>
          )}
          {search.isPending && (
            <li className="text-muted-foreground px-3 py-2 text-sm" role="presentation">
              Searching…
            </li>
          )}
        </ul>
      )}
    </div>
  )
}
