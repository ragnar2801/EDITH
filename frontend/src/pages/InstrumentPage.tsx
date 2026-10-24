import { ArrowLeft } from 'lucide-react'
import { useState, type FormEvent, type ReactNode } from 'react'
import { Link, useParams } from 'react-router'

import { useClearClassification, useInstrument, useSetClassification } from '@/api/queries'
import type { Schemas } from '@/api/client'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  ASSET_CLASS_LABELS,
  BUCKET_LABELS,
  BUCKETS,
  EXPOSURE_LABELS,
  KIND_LABELS,
  exchangeLabel,
  listingLabel,
  planLabel,
  type Bucket,
  type Exposure,
  type InstrumentDetail,
} from '@/lib/instruments'
import { formatDate, formatDateTime } from '@/lib/time'
import { cn } from '@/lib/utils'

type Classification = Schemas['ClassificationOut']

const BUCKET_COLOURS: Record<Bucket, string> = {
  equity: 'bg-bucket-equity',
  debt: 'bg-bucket-debt',
  gold: 'bg-bucket-gold',
  silver: 'bg-bucket-silver',
  other: 'bg-bucket-other',
}

export function InstrumentPage() {
  const id = Number(useParams().id)
  const instrument = useInstrument(id)

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <Link
        to="/instruments"
        className="text-muted-foreground hover:text-foreground flex w-fit items-center gap-1 text-sm"
      >
        <ArrowLeft className="size-4" aria-hidden /> Instruments
      </Link>
      {instrument.isPending && <p className="text-muted-foreground">Loading…</p>}
      {instrument.isError && (
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Instrument not found</h1>
          <p className="text-muted-foreground mt-1">{instrument.error.message}</p>
        </div>
      )}
      {instrument.isSuccess && <Details instrument={instrument.data} />}
    </div>
  )
}

function Details({ instrument }: { instrument: InstrumentDetail }) {
  const plan = planLabel(instrument)
  return (
    <>
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">{instrument.name}</h1>
        <div className="text-muted-foreground flex flex-wrap items-center gap-2 text-sm">
          <span>{listingLabel(instrument)}</span>
          {plan && <span>· {plan}</span>}
          <Badge variant="outline">{KIND_LABELS[instrument.kind]}</Badge>
          <Badge variant="outline">{ASSET_CLASS_LABELS[instrument.asset_class]}</Badge>
          <Badge variant="outline">{EXPOSURE_LABELS[instrument.exposure]}</Badge>
          <Badge variant="outline">{instrument.currency}</Badge>
          {!instrument.is_active && <Badge variant="secondary">inactive</Badge>}
        </div>
      </div>
      <ClassificationCard instrument={instrument} />
      <IdentifiersCard instrument={instrument} />
      {instrument.variants.length > 0 && <VariantsCard instrument={instrument} />}
      {instrument.aliases.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Also known as</CardTitle>
            <CardDescription>Earlier symbols and names. Search finds these too.</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="text-sm">
              {instrument.aliases.map((alias) => (
                <li key={`${alias.kind}-${alias.value}`} className="py-0.5">
                  {alias.value}{' '}
                  <span className="text-muted-foreground">
                    ({alias.kind}
                    {alias.changed_on && `, until ${formatDate(alias.changed_on)}`})
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </>
  )
}

function IdentifiersCard({ instrument }: { instrument: InstrumentDetail }) {
  const rows: [string, ReactNode][] = [
    ['Exchange', instrument.exchange && exchangeLabel(instrument.exchange)],
    ['Symbol', instrument.symbol],
    ['NSE series', instrument.series],
    ['ISIN', instrument.isin],
    ['ISIN (reinvestment)', instrument.isin_reinvestment],
    ['AMFI scheme code', instrument.amfi_code],
    ['SEC CIK', instrument.cik],
    ['Fund house', instrument.fund_house],
    ['Category', instrument.fund_category],
    ['Scheme type', instrument.scheme_type],
    ['Listed on', instrument.listed_on && formatDate(instrument.listed_on)],
    ['Market', instrument.market === 'IN' ? 'India' : 'US'],
    ['Currency', instrument.currency],
    [
      'Status',
      instrument.is_active ? 'Active' : 'Inactive: no longer on its list, or no recent NAV',
    ],
    ['Last changed', formatDateTime(instrument.updated_at)],
  ]
  return (
    <Card>
      <CardHeader>
        <CardTitle>Details</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-[minmax(8rem,auto)_1fr] gap-x-6 gap-y-1.5 text-sm">
          {rows
            .filter(([, value]) => value)
            .map(([label, value]) => (
              <div key={label} className="contents">
                <dt className="text-muted-foreground">{label}</dt>
                <dd className="break-all">{value}</dd>
              </div>
            ))}
        </dl>
      </CardContent>
    </Card>
  )
}

function VariantsCard({ instrument }: { instrument: InstrumentDetail }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Other plans and options</CardTitle>
        <CardDescription>Each has its own scheme code and NAV.</CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="text-sm">
          {instrument.variants.map((variant) => (
            <li key={variant.id} className="py-0.5">
              <Link to={`/instruments/${variant.id}`} className="underline underline-offset-4">
                {planLabel(variant) || 'Plan'}
              </Link>{' '}
              <span className="text-muted-foreground">AMFI {variant.amfi_code}</span>
              {!variant.is_active && <span className="text-muted-foreground"> · inactive</span>}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}

function AllocationBar({ classification }: { classification: Classification }) {
  if (classification.allocation.length === 0) {
    return <p className="text-muted-foreground text-sm">Not classified yet.</p>
  }
  return (
    <div className="flex flex-col gap-2">
      <div className="bg-muted flex h-2.5 overflow-hidden rounded-full" aria-hidden>
        {classification.allocation.map((share) => (
          <div
            key={share.bucket}
            className={BUCKET_COLOURS[share.bucket]}
            style={{ width: `${share.percent}%` }}
          />
        ))}
      </div>
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
        {classification.allocation.map((share) => (
          <li key={share.bucket} className="flex items-center gap-1.5">
            <span aria-hidden className={cn('size-2.5 rounded-sm', BUCKET_COLOURS[share.bucket])} />
            {BUCKET_LABELS[share.bucket]} {share.percent}%
          </li>
        ))}
        <li className="text-muted-foreground">
          Exposure: {EXPOSURE_LABELS[classification.exposure]}
        </li>
      </ul>
    </div>
  )
}

function ClassificationCard({ instrument }: { instrument: InstrumentDetail }) {
  const [editing, setEditing] = useState(false)
  const clear = useClearClassification(instrument.id)
  const override = instrument.override

  return (
    <Card>
      <CardHeader>
        <CardTitle>Classification</CardTitle>
        <CardDescription>
          {override
            ? 'Your own classification. The rules are ignored for this instrument.'
            : 'From the rules: NSE’s ETF type, the AMFI category or the name.'}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <AllocationBar classification={override ?? instrument.rule} />
        {override?.note && <p className="text-sm">Note: {override.note}</p>}
        {override && (
          <div className="text-muted-foreground text-sm">
            <p className="mb-1">The rules would say:</p>
            <AllocationBar classification={instrument.rule} />
          </div>
        )}
        {editing ? (
          <OverrideForm instrument={instrument} onDone={() => setEditing(false)} />
        ) : (
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
              {override ? 'Change my classification' : 'Set my own classification'}
            </Button>
            {override && (
              <Button
                variant="ghost"
                size="sm"
                disabled={clear.isPending}
                onClick={() => clear.mutate()}
              >
                Use the rules again
              </Button>
            )}
          </div>
        )}
        {clear.isError && <p className="text-destructive text-sm">{clear.error.message}</p>}
      </CardContent>
    </Card>
  )
}

function OverrideForm({
  instrument,
  onDone,
}: {
  instrument: InstrumentDetail
  onDone: () => void
}) {
  const current = instrument.override ?? instrument.rule
  const [percents, setPercents] = useState<Record<Bucket, string>>(
    () =>
      Object.fromEntries(
        BUCKETS.map((bucket) => [
          bucket,
          current.allocation.find((share) => share.bucket === bucket)?.percent ?? '',
        ]),
      ) as Record<Bucket, string>,
  )
  const [exposure, setExposure] = useState<Exposure>(current.exposure)
  const [note, setNote] = useState(instrument.override?.note ?? '')
  const save = useSetClassification(instrument.id)

  function submit(event: FormEvent) {
    event.preventDefault()
    const allocation = BUCKETS.filter((bucket) => percents[bucket].trim() !== '').map((bucket) => ({
      bucket,
      percent: percents[bucket].trim(),
    }))
    save.mutate({ allocation, exposure, note: note.trim() || null }, { onSuccess: onDone })
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4" aria-label="My classification">
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-sm font-medium">Split in percent (must add up to 100)</legend>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          {BUCKETS.map((bucket) => (
            <label key={bucket} className="flex flex-col gap-1 text-sm">
              {BUCKET_LABELS[bucket]}
              <Input
                inputMode="decimal"
                placeholder="0"
                value={percents[bucket]}
                onChange={(event) =>
                  setPercents((previous) => ({ ...previous, [bucket]: event.target.value }))
                }
              />
            </label>
          ))}
        </div>
      </fieldset>
      <div className="grid gap-3 sm:grid-cols-[auto_1fr]">
        <label className="flex flex-col gap-1 text-sm">
          Exposure
          <select
            className="border-input dark:bg-input/30 h-9 rounded-md border bg-transparent px-3 text-sm"
            value={exposure}
            onChange={(event) => setExposure(event.target.value as Exposure)}
          >
            {Object.entries(EXPOSURE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Note (optional)
          <Input
            value={note}
            maxLength={500}
            placeholder="Why, e.g. from the March factsheet"
            onChange={(event) => setNote(event.target.value)}
          />
        </label>
      </div>
      {save.isError && (
        <p role="alert" className="text-destructive text-sm">
          {save.error.message}
        </p>
      )}
      <div className="flex gap-2">
        <Button type="submit" size="sm" disabled={save.isPending}>
          Save
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={onDone}>
          Cancel
        </Button>
      </div>
    </form>
  )
}
