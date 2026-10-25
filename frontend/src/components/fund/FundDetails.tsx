import { useState, type FormEvent, type ReactNode } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'

import { useClearClassification, useSetClassification } from '@/api/queries'
import type { Schemas } from '@/api/client'
import { ErrorText } from '@/components/Field'
import { InfoTip } from '@/components/InfoTip'
import { Section } from '@/components/Section'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import {
  BUCKET_LABELS,
  BUCKETS,
  EXPOSURE_LABELS,
  exchangeLabel,
  fundPath,
  planLabel,
  type Bucket,
  type Exposure,
  type InstrumentDetail,
} from '@/lib/instruments'
import { formatDate } from '@/lib/time'
import { cn } from '@/lib/utils'

type Classification = Schemas['ClassificationOut']

const BUCKET_COLOURS: Record<Bucket, string> = {
  equity: 'bg-bucket-equity',
  debt: 'bg-bucket-debt',
  gold: 'bg-bucket-gold',
  silver: 'bg-bucket-silver',
  other: 'bg-bucket-other',
}

/** Everything about a fund that isn't money: classification, identifiers, other plans. */
export function FundDetails({ instrument }: { instrument: InstrumentDetail }) {
  return (
    <div className="flex flex-col gap-8">
      <ClassificationSection instrument={instrument} />
      <Identifiers instrument={instrument} />
      {instrument.variants.length > 0 && <Variants instrument={instrument} />}
      {instrument.aliases.length > 0 && (
        <Section title="Earlier names">
          <ul className="text-sm">
            {instrument.aliases.map((alias) => (
              <li key={`${alias.kind}-${alias.value}`} className="py-0.5">
                {alias.value}
                {alias.changed_on && (
                  <span className="text-muted-foreground">
                    {' '}
                    · until {formatDate(alias.changed_on)}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  )
}

function Identifiers({ instrument }: { instrument: InstrumentDetail }) {
  const rows: [string, ReactNode][] = [
    ['Fund house', instrument.fund_house],
    ['Category', instrument.fund_category],
    ['Scheme type', instrument.scheme_type],
    ['AMFI scheme code', instrument.amfi_code],
    ['ISIN', instrument.isin],
    ['Exchange', instrument.exchange && exchangeLabel(instrument.exchange)],
    ['Symbol', instrument.symbol],
    ['Listed on', instrument.listed_on && formatDate(instrument.listed_on)],
  ]
  return (
    <Section title="Identifiers">
      <dl className="grid grid-cols-[minmax(8rem,auto)_1fr] gap-x-6 gap-y-1.5 text-sm">
        {rows
          .filter(([, value]) => value)
          .map(([label, value]) => (
            <div key={label} className="contents">
              <dt className="text-muted-foreground">{label}</dt>
              <dd className="break-words">{value}</dd>
            </div>
          ))}
      </dl>
    </Section>
  )
}

function Variants({ instrument }: { instrument: InstrumentDetail }) {
  return (
    <Section title="Other plans">
      <ul className="text-sm">
        {instrument.variants.map((variant) => (
          <li key={variant.id} className="py-0.5">
            <Link to={fundPath(variant.id)} className="underline underline-offset-4">
              {planLabel(variant) || 'Plan'}
            </Link>{' '}
            <span className="text-muted-foreground">AMFI {variant.amfi_code}</span>
            {!variant.is_active && <span className="text-muted-foreground"> · inactive</span>}
          </li>
        ))}
      </ul>
    </Section>
  )
}

function ClassificationSection({ instrument }: { instrument: InstrumentDetail }) {
  const [editing, setEditing] = useState(false)
  const clear = useClearClassification(instrument.id)
  const override = instrument.override

  return (
    <Section
      title="Classification"
      info={
        <InfoTip label="Classification">
          {override
            ? 'Your own split; the rules are ignored for this fund.'
            : 'From the rules: the AMFI category or the name.'}
        </InfoTip>
      }
      actions={
        <>
          {override && (
            <Button
              variant="ghost"
              size="sm"
              disabled={clear.isPending}
              onClick={() =>
                clear.mutate(undefined, { onSuccess: () => toast.success('Using the rules again') })
              }
            >
              Use the rules
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
            {override ? 'Change' : 'Set my own'}
          </Button>
        </>
      }
    >
      <AllocationBar classification={override ?? instrument.rule} />
      {override?.note && <p className="text-sm">Note: {override.note}</p>}
      {override && (
        <div className="text-muted-foreground flex flex-col gap-1 text-sm">
          <span className="text-xs font-medium">The rules would say</span>
          <AllocationBar classification={instrument.rule} />
        </div>
      )}
      <ErrorText error={clear.error} />
      <Dialog open={editing} onOpenChange={setEditing}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>My classification</DialogTitle>
            <DialogDescription>{instrument.name}</DialogDescription>
          </DialogHeader>
          {editing && <OverrideForm instrument={instrument} onDone={() => setEditing(false)} />}
        </DialogContent>
      </Dialog>
    </Section>
  )
}

function AllocationBar({ classification }: { classification: Classification }) {
  if (classification.allocation.length === 0) {
    return <p className="text-muted-foreground text-sm">Not classified</p>
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
    save.mutate(
      { allocation, exposure, note: note.trim() || null },
      {
        onSuccess: () => {
          toast.success('Classification saved')
          onDone()
        },
      },
    )
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4" aria-label="My classification">
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 flex items-center gap-1.5 text-sm font-medium">
          Split (%)
          <InfoTip label="Split">Must add up to 100.</InfoTip>
        </legend>
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
          Note
          <Input
            value={note}
            maxLength={500}
            placeholder="From the March factsheet"
            onChange={(event) => setNote(event.target.value)}
          />
        </label>
      </div>
      <ErrorText error={save.error} />
      <DialogFooter>
        <Button type="button" variant="ghost" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" disabled={save.isPending}>
          Save
        </Button>
      </DialogFooter>
    </form>
  )
}
