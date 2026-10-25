import { Loader2, Plus, X } from 'lucide-react'
import { useId, useState, type FormEvent } from 'react'
import { Link } from 'react-router'

import { useBuckets, useDefaultBenchmark, useDeleteBucket, useSaveBucket } from '@/api/queries'
import type { Schemas } from '@/api/client'
import { InstrumentSearch } from '@/components/InstrumentSearch'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { NativeSelect } from '@/components/ui/native-select'
import { REBALANCE_LABELS, type Bucket, type Rebalance } from '@/lib/buckets'
import { planLabel } from '@/lib/instruments'
import { formatDate } from '@/lib/time'
import { cn } from '@/lib/utils'
import { equalWeights, fromBasisPoints, totalBasisPoints } from '@/lib/weights'

type FundRef = Schemas['FundRef']

type Draft = {
  id?: number
  name: string
  description: string
  rebalance: Rebalance
  benchmark: FundRef | null
  funds: { fund: FundRef; weight: string }[]
}

export function BucketsPage() {
  const buckets = useBuckets()
  const defaultBenchmark = useDefaultBenchmark()
  const [draft, setDraft] = useState<Draft | null>(null)

  function startNew() {
    setDraft({
      name: '',
      description: '',
      rebalance: 'none',
      benchmark: defaultBenchmark.data ?? null,
      funds: [],
    })
  }

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Buckets</h1>
          <p className="text-muted-foreground mt-1">
            A bucket is a target split: funds with weights that add up to 100%, a rebalance policy
            and a benchmark. Backtest it, and later use it as your target.
          </p>
        </div>
        {!draft && (
          <Button onClick={startNew}>
            <Plus /> New bucket
          </Button>
        )}
      </div>

      {draft && <BucketEditor draft={draft} onDone={() => setDraft(null)} />}

      {buckets.isError && <p className="text-destructive text-sm">{buckets.error.message}</p>}
      {buckets.isSuccess && buckets.data.length === 0 && !draft && (
        <Card>
          <CardHeader>
            <CardTitle>No buckets yet</CardTitle>
            <CardDescription>
              Start with your current split, e.g. 40% flexi cap, 25% large cap, 20% mid cap, 15%
              small cap.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={startNew}>
              <Plus /> New bucket
            </Button>
          </CardContent>
        </Card>
      )}
      <div className="grid gap-4 md:grid-cols-2">
        {buckets.data?.map((bucket) => (
          <BucketCard
            key={bucket.id}
            bucket={bucket}
            onEdit={() =>
              setDraft({
                id: bucket.id,
                name: bucket.name,
                description: bucket.description ?? '',
                rebalance: bucket.rebalance,
                benchmark: bucket.benchmark?.fund ?? null,
                funds: bucket.funds.map((member) => ({
                  fund: member.fund,
                  weight: member.weight,
                })),
              })
            }
          />
        ))}
      </div>
    </div>
  )
}

function FundName({ fund }: { fund: FundRef }) {
  const plan = planLabel(fund)
  return (
    <span className="flex min-w-0 flex-col">
      <span className="truncate font-medium">{fund.name}</span>
      <span className="text-muted-foreground truncate text-xs">
        AMFI {fund.amfi_code}
        {plan && ` · ${plan}`}
      </span>
    </span>
  )
}

function BucketCard({ bucket, onEdit }: { bucket: Bucket; onEdit: () => void }) {
  const remove = useDeleteBucket()
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2">
          {bucket.name}
          <Badge variant="outline">{REBALANCE_LABELS[bucket.rebalance]}</Badge>
        </CardTitle>
        {bucket.description && <CardDescription>{bucket.description}</CardDescription>}
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <ul className="flex flex-col gap-1.5 text-sm">
          {bucket.funds.map((member) => (
            <li key={member.fund.id} className="flex items-center justify-between gap-3">
              <Link
                to={`/instruments/${member.fund.id}`}
                className="min-w-0 truncate underline-offset-4 hover:underline"
              >
                {member.fund.name}
                {planLabel(member.fund) && (
                  <span className="text-muted-foreground"> · {planLabel(member.fund)}</span>
                )}
              </Link>
              <span className="tabular-nums">{member.weight}%</span>
            </li>
          ))}
        </ul>
        <p className="text-muted-foreground text-xs">
          {bucket.benchmark ? `vs ${bucket.benchmark.fund.name}` : 'No benchmark'}
          {bucket.common_start && ` · NAVs for all funds from ${formatDate(bucket.common_start)}`}
        </p>
        <div className="flex flex-wrap gap-2">
          <Button asChild size="sm">
            <Link to={`/backtest/${bucket.id}`}>Backtest</Link>
          </Button>
          <Button size="sm" variant="outline" onClick={onEdit}>
            Edit
          </Button>
          <Button
            size="sm"
            variant="ghost"
            disabled={remove.isPending}
            onClick={() => {
              if (confirm(`Delete the bucket “${bucket.name}” and its saved backtests?`)) {
                remove.mutate(bucket.id)
              }
            }}
          >
            Delete
          </Button>
        </div>
        {remove.isError && (
          <p role="alert" className="text-destructive text-sm">
            {remove.error.message}
          </p>
        )}
      </CardContent>
    </Card>
  )
}

function BucketEditor({ draft: initial, onDone }: { draft: Draft; onDone: () => void }) {
  const [draft, setDraft] = useState(initial)
  const save = useSaveBucket()
  const nameId = useId()
  const descriptionId = useId()
  const rebalanceId = useId()
  const total = totalBasisPoints(draft.funds.map((member) => member.weight))

  function update(patch: Partial<Draft>) {
    setDraft((current) => ({ ...current, ...patch }))
  }

  function setWeight(index: number, weight: string) {
    update({
      funds: draft.funds.map((member, i) => (i === index ? { ...member, weight } : member)),
    })
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    save.mutate(
      {
        id: draft.id,
        body: {
          name: draft.name,
          description: draft.description || null,
          rebalance: draft.rebalance,
          benchmark_id: draft.benchmark?.id ?? null,
          funds: draft.funds.map((member) => ({
            instrument_id: member.fund.id,
            weight: member.weight.trim(),
          })),
        },
      },
      { onSuccess: onDone },
    )
  }

  return (
    <Card className="border-primary/40">
      <CardHeader>
        <CardTitle>{draft.id ? 'Edit bucket' : 'New bucket'}</CardTitle>
        <CardDescription>
          Funds only for now. Weights are percentages with up to 2 decimals and must add up to
          exactly 100.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form aria-label="Bucket" className="flex flex-col gap-5" onSubmit={submit}>
          <div className="grid gap-4 sm:grid-cols-[2fr_1fr]">
            <div className="flex flex-col gap-1.5">
              <label htmlFor={nameId} className="text-sm font-medium">
                Name
              </label>
              <Input
                id={nameId}
                value={draft.name}
                placeholder="e.g. Core 40/25/20/15"
                onChange={(event) => update({ name: event.target.value })}
                required
                maxLength={120}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor={rebalanceId} className="text-sm font-medium">
                Rebalance
              </label>
              <NativeSelect
                id={rebalanceId}
                value={draft.rebalance}
                onChange={(event) => update({ rebalance: event.target.value as Rebalance })}
              >
                {(Object.keys(REBALANCE_LABELS) as Rebalance[]).map((key) => (
                  <option key={key} value={key}>
                    {REBALANCE_LABELS[key]}
                  </option>
                ))}
              </NativeSelect>
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor={descriptionId} className="text-sm font-medium">
              Description (optional)
            </label>
            <Input
              id={descriptionId}
              value={draft.description}
              maxLength={500}
              onChange={(event) => update({ description: event.target.value })}
            />
          </div>

          <fieldset className="flex flex-col gap-2">
            <legend className="mb-1 flex w-full items-center justify-between gap-2 text-sm font-medium">
              Funds
              <span className="flex items-center gap-2">
                <Badge
                  variant="outline"
                  className={cn(total === 10_000 ? 'text-positive' : 'text-destructive')}
                >
                  Total {total === null ? '?' : fromBasisPoints(total)}%
                </Badge>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  disabled={draft.funds.length === 0}
                  onClick={() => {
                    const weights = equalWeights(draft.funds.length)
                    update({
                      funds: draft.funds.map((member, i) => ({ ...member, weight: weights[i] })),
                    })
                  }}
                >
                  Equal weights
                </Button>
              </span>
            </legend>
            {draft.funds.length === 0 && (
              <p className="text-muted-foreground text-sm">Add funds with the search below.</p>
            )}
            <ul className="flex flex-col divide-y rounded-md border">
              {draft.funds.map((member, index) => (
                <li key={member.fund.id} className="flex items-center gap-3 px-3 py-2">
                  <FundName fund={member.fund} />
                  <span className="ml-auto flex shrink-0 items-center gap-1">
                    <Input
                      aria-label={`Weight of ${member.fund.name}`}
                      className="w-20 text-right"
                      inputMode="decimal"
                      value={member.weight}
                      onChange={(event) => setWeight(index, event.target.value)}
                    />
                    <span className="text-muted-foreground text-sm">%</span>
                    <Button
                      type="button"
                      size="icon"
                      variant="ghost"
                      aria-label={`Remove ${member.fund.name}`}
                      onClick={() => update({ funds: draft.funds.filter((_, i) => i !== index) })}
                    >
                      <X />
                    </Button>
                  </span>
                </li>
              ))}
            </ul>
            <InstrumentSearch
              kind="mutual_fund"
              label="Add a fund"
              placeholder="Add a fund: name or AMFI scheme code"
              onSelect={(fund) => {
                if (draft.funds.some((member) => member.fund.id === fund.id)) return
                update({ funds: [...draft.funds, { fund, weight: '' }] })
              }}
            />
          </fieldset>

          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium">Benchmark</span>
            {draft.benchmark ? (
              <div className="flex items-center gap-3 rounded-md border px-3 py-2">
                <FundName fund={draft.benchmark} />
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  className="ml-auto"
                  onClick={() => update({ benchmark: null })}
                >
                  Remove
                </Button>
              </div>
            ) : (
              <InstrumentSearch
                kind="mutual_fund"
                label="Choose a benchmark"
                placeholder="Benchmark fund, e.g. Nifty 50 index fund"
                onSelect={(fund) => update({ benchmark: fund })}
              />
            )}
            <p className="text-muted-foreground text-xs">
              The default is a Nifty 50 index fund: backtests compare the bucket with the same money
              in it.
            </p>
          </div>

          {save.isError && (
            <p role="alert" className="text-destructive text-sm">
              {save.error.message}
            </p>
          )}
          <div className="flex flex-wrap justify-end gap-2">
            <Button type="button" variant="ghost" onClick={onDone}>
              Cancel
            </Button>
            <Button type="submit" disabled={save.isPending}>
              {save.isPending && <Loader2 className="animate-spin" />}
              {save.isPending ? 'Saving and downloading NAVs…' : 'Save bucket'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
