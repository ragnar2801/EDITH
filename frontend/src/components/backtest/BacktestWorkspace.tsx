import { FlaskConical, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useLocation } from 'react-router'
import { toast } from 'sonner'

import {
  useDeleteBacktest,
  useLoadBacktest,
  useRunBacktest,
  useSaveBacktest,
  useSavedBacktests,
  type BacktestRun,
} from '@/api/queries'
import { EmptyState } from '@/components/EmptyState'
import { ErrorText } from '@/components/Field'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { NativeSelect } from '@/components/ui/native-select'
import { useConfirm } from '@/hooks/use-confirm'
import { DEFAULT_FORM, STRATEGY_LABELS, fromRun, modelSplit, toParams } from '@/lib/backtest'
import type { Bucket } from '@/lib/buckets'
import type { BacktestHandoff } from '@/lib/optimise'
import { formatDateTime } from '@/lib/time'

import { BacktestControls } from './BacktestControls'
import { BacktestResults } from './BacktestResults'

/** Backtests of one model, ported from Friday: controls on the left, results right.
 * Each run is compared with the one shown before it; a split tried from Optimise
 * arrives filled in. */
export function BacktestWorkspace({ bucket }: { bucket: Bucket }) {
  const handed = useLocation().state as BacktestHandoff | null
  const [form, setForm] = useState(() => ({
    ...DEFAULT_FORM,
    split: modelSplit(bucket),
    ...handed?.form,
  }))
  const [shown, setShown] = useState<BacktestRun | null>(null)
  const [previous, setPrevious] = useState<BacktestRun | null>(null)
  const run = useRunBacktest()
  const load = useLoadBacktest()
  const current = shown && shown.bucket_id === bucket.id ? shown : null
  const baseline =
    current && previous && previous.bucket_id === bucket.id && previous.id !== current.id
      ? previous
      : null

  function show(next: BacktestRun) {
    setPrevious(current)
    setShown(next)
  }

  return (
    <div className="grid items-start gap-6 lg:grid-cols-[18rem_minmax(0,1fr)]">
      <Card className="lg:sticky lg:top-20">
        <CardContent className="flex flex-col gap-5">
          <BacktestControls
            bucket={bucket}
            form={form}
            onForm={setForm}
            running={run.isPending}
            onRun={() =>
              run.mutate(
                { bucket_id: bucket.id, params: toParams(form, bucket), save: false },
                { onSuccess: show },
              )
            }
          />
          <ErrorText error={run.error} />
          <SavedRuns
            bucketId={bucket.id}
            current={current}
            loading={load.isPending}
            onLoad={(id) =>
              load.mutate(id, {
                onSuccess: (loaded) => {
                  show(loaded)
                  setForm(fromRun(loaded, bucket))
                },
              })
            }
            onDeleted={(id) => current?.id === id && setShown(null)}
          />
        </CardContent>
      </Card>

      {current ? (
        <BacktestResults
          key={current.id}
          run={current}
          baseline={baseline}
          onClearBaseline={() => setPrevious(null)}
        />
      ) : (
        <EmptyState icon={FlaskConical} title={`Ready to backtest ${bucket.name}`} />
      )}
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
  const confirm = useConfirm()

  return (
    <div className="flex flex-col gap-3 border-t pt-4">
      {current && !current.saved && (
        <form
          aria-label="Save this run"
          className="flex gap-2"
          onSubmit={(event) => {
            event.preventDefault()
            save.mutate(
              { id: current.id, name },
              {
                onSuccess: () => {
                  setName('')
                  toast.success('Run saved')
                },
              },
            )
          }}
        >
          <Input
            aria-label="Name for this run"
            placeholder="Name"
            value={name}
            maxLength={120}
            onChange={(event) => setName(event.target.value)}
          />
          <Button type="submit" variant="outline" disabled={save.isPending}>
            Save run
          </Button>
        </form>
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
              onClick={async () => {
                if (!picked || !(await confirm({ title: 'Delete this saved run?' }))) return
                remove.mutate(
                  { id: picked, bucketId },
                  {
                    onSuccess: () => {
                      onDeleted(picked)
                      setPicked(null)
                      toast.success('Saved run deleted')
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
