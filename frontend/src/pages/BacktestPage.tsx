import { Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'

import {
  useBuckets,
  useDeleteBacktest,
  useLoadBacktest,
  useRunBacktest,
  useSaveBacktest,
  useSavedBacktests,
  type BacktestRun,
} from '@/api/queries'
import { BacktestControls } from '@/components/backtest/BacktestControls'
import { BacktestResults } from '@/components/backtest/BacktestResults'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { NativeSelect } from '@/components/ui/native-select'
import { DEFAULT_FORM, STRATEGY_LABELS, fromParams, toParams } from '@/lib/backtest'
import { formatDateTime } from '@/lib/time'

/** Backtests of a bucket (T1-14), ported from Friday: controls on the left, results right. */
export function BacktestPage() {
  const params = useParams()
  const navigate = useNavigate()
  const bucketId = params.bucketId ? Number(params.bucketId) : null
  const buckets = useBuckets()
  const bucket = buckets.data?.find((b) => b.id === bucketId) ?? null

  const [form, setForm] = useState(DEFAULT_FORM)
  const [shown, setShown] = useState<BacktestRun | null>(null)
  const run = useRunBacktest()
  const load = useLoadBacktest()
  const current = shown && shown.bucket_id === bucketId ? shown : null

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Backtest</h1>
        <p className="text-muted-foreground mt-1">
          How a bucket would have done on its funds’ real NAVs: a lump sum, a SIP, an SWP, or your
          own timeline of buys and sells, next to the same money in its benchmark.
        </p>
      </div>
      <div className="grid items-start gap-6 lg:grid-cols-[18rem_minmax(0,1fr)]">
        <Card className="lg:sticky lg:top-6">
          <CardContent className="flex flex-col gap-5">
            <BacktestControls
              buckets={buckets.data ?? []}
              bucket={bucket}
              onBucket={(id) => {
                setShown(null)
                setForm((f) => ({
                  ...f,
                  positions: DEFAULT_FORM.positions,
                  trades: DEFAULT_FORM.trades,
                }))
                navigate(id ? `/backtest/${id}` : '/backtest')
              }}
              form={form}
              onForm={setForm}
              running={run.isPending}
              onRun={() =>
                bucket &&
                run.mutate(
                  { bucket_id: bucket.id, params: toParams(form), save: false },
                  { onSuccess: setShown },
                )
              }
            />
            {run.isError && (
              <p role="alert" className="text-destructive text-sm">
                {run.error.message}
              </p>
            )}
            {bucket && (
              <SavedRuns
                bucketId={bucket.id}
                current={current}
                loading={load.isPending}
                onLoad={(id) =>
                  load.mutate(id, {
                    onSuccess: (loaded) => {
                      setShown(loaded)
                      setForm(fromParams(loaded.params))
                    },
                  })
                }
                onDeleted={(id) => current?.id === id && setShown(null)}
              />
            )}
          </CardContent>
        </Card>

        {current ? (
          <BacktestResults key={current.id} run={current} />
        ) : buckets.isSuccess && buckets.data.length === 0 ? (
          <Card>
            <CardHeader>
              <CardTitle>No buckets yet</CardTitle>
              <CardDescription>
                <Link to="/buckets" className="underline underline-offset-4">
                  Create a bucket
                </Link>{' '}
                first, then backtest it here.
              </CardDescription>
            </CardHeader>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>
                {bucket ? `Ready to backtest ${bucket.name}` : 'Choose a bucket'}
              </CardTitle>
              <CardDescription>
                {bucket
                  ? 'Pick a strategy and its amounts on the left, then run.'
                  : 'Pick a bucket on the left.'}
              </CardDescription>
            </CardHeader>
          </Card>
        )}
      </div>
    </div>
  )
}

function SavedRuns({
  bucketId,
  current,
  loading,
  onLoad,
  onDeleted,
}: {
  bucketId: number
  current: BacktestRun | null
  loading: boolean
  onLoad: (id: number) => void
  onDeleted: (id: number) => void
}) {
  const saved = useSavedBacktests(bucketId)
  const save = useSaveBacktest()
  const remove = useDeleteBacktest()
  const [name, setName] = useState('')
  const [picked, setPicked] = useState<number | null>(null)

  return (
    <div className="flex flex-col gap-3 border-t pt-4">
      {current && !current.saved && (
        <form
          aria-label="Save this run"
          className="flex gap-2"
          onSubmit={(event) => {
            event.preventDefault()
            save.mutate({ id: current.id, name }, { onSuccess: () => setName('') })
          }}
        >
          <Input
            aria-label="Name for this run"
            placeholder="Name (optional)"
            value={name}
            maxLength={120}
            onChange={(event) => setName(event.target.value)}
          />
          <Button type="submit" variant="outline" disabled={save.isPending}>
            Save run
          </Button>
        </form>
      )}
      {save.isSuccess && current?.id === save.data.id && (
        <p className="text-muted-foreground text-xs">Saved.</p>
      )}
      {saved.data && saved.data.length > 0 && (
        <div className="flex flex-col gap-1">
          <label htmlFor="saved-runs" className="text-muted-foreground text-xs font-medium">
            Saved runs
          </label>
          <div className="flex gap-1">
            <NativeSelect
              id="saved-runs"
              value={picked ?? ''}
              disabled={loading}
              onChange={(event) => {
                const id = event.target.value ? Number(event.target.value) : null
                setPicked(id)
                if (id) onLoad(id)
              }}
            >
              <option value="">Load a saved run…</option>
              {saved.data.map((summary) => (
                <option key={summary.id} value={summary.id}>
                  {summary.name ?? STRATEGY_LABELS[summary.strategy]} ·{' '}
                  {formatDateTime(summary.created_at)}
                </option>
              ))}
            </NativeSelect>
            <Button
              type="button"
              size="icon"
              variant="ghost"
              aria-label="Delete the saved run"
              disabled={!picked || remove.isPending}
              onClick={() => {
                if (!picked || !confirm('Delete this saved run?')) return
                remove.mutate(
                  { id: picked, bucketId },
                  {
                    onSuccess: () => {
                      onDeleted(picked)
                      setPicked(null)
                    },
                  },
                )
              }}
            >
              <Trash2 />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
