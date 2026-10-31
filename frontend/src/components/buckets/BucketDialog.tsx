import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'

import { useModels, useSaveBucket, type Bucket } from '@/api/queries'
import { ErrorText, Field } from '@/components/Field'
import { InfoTip } from '@/components/InfoTip'
import { Segmented } from '@/components/Segmented'
import { Button } from '@/components/ui/button'
import {
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { NativeSelect } from '@/components/ui/native-select'

const MONEY = { real: 'Real', paper: 'Paper' } as const

const BUCKET_INFO = {
  model: 'The split new money in this bucket moves towards.',
  money: 'Paper buys pretend units at real NAVs, kept out of your totals.',
}

/** Make a bucket, or change one: name, model, real or paper. Goes inside a `Dialog`. */
export function BucketDialog({
  bucket,
  onDone,
}: {
  bucket?: Bucket
  onDone: (saved?: Bucket) => void
}) {
  const models = useModels()
  const save = useSaveBucket()
  const [draft, setDraft] = useState({
    name: bucket?.name ?? '',
    model: bucket?.model ? String(bucket.model.id) : '',
    money: bucket?.paper ? 'paper' : ('real' as keyof typeof MONEY),
  })
  // Real and paper purchases never mix: only an empty bucket can switch.
  const fixed = !!bucket && (bucket.from_fm || bucket.purchases > 0)

  function submit(event: FormEvent) {
    event.preventDefault()
    save.mutate(
      {
        id: bucket?.id,
        body: {
          name: draft.name,
          model_id: draft.model ? Number(draft.model) : null,
          paper: draft.money === 'paper',
        },
      },
      {
        onSuccess: (saved) => {
          toast.success(bucket ? `${saved.name} saved` : `${saved.name} made`)
          onDone(saved)
        },
      },
    )
  }

  const title = bucket ? `Edit ${bucket.name}` : 'New bucket'
  return (
    <DialogContent>
      <DialogHeader>
        <DialogTitle>{title}</DialogTitle>
        <DialogDescription className="sr-only">Name, model, and real or paper</DialogDescription>
      </DialogHeader>
      <form aria-label={title} className="flex flex-col gap-4" onSubmit={submit}>
        <Field label="Name">
          {(id) => (
            <Input
              id={id}
              required
              disabled={bucket?.from_fm}
              value={draft.name}
              placeholder="Retirement"
              onChange={(event) => setDraft({ ...draft, name: event.target.value })}
            />
          )}
        </Field>
        <Field label="Model" info={BUCKET_INFO.model}>
          {(id) => (
            <NativeSelect
              id={id}
              value={draft.model}
              onChange={(event) => setDraft({ ...draft, model: event.target.value })}
            >
              <option value="">No model</option>
              {models.data?.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name}
                </option>
              ))}
            </NativeSelect>
          )}
        </Field>
        <div className="flex flex-col gap-1.5">
          <span className="flex items-center gap-1.5 text-sm font-medium">
            Money
            <InfoTip label="Money">{BUCKET_INFO.money}</InfoTip>
          </span>
          <Segmented
            label="Money"
            value={draft.money}
            options={MONEY}
            disabled={fixed ? (['real', 'paper'] as const).filter((m) => m !== draft.money) : []}
            onChange={(money) => setDraft({ ...draft, money })}
          />
        </div>
        <ErrorText error={save.error} />
        <DialogFooter>
          <Button type="button" variant="ghost" onClick={() => onDone()}>
            Cancel
          </Button>
          <Button type="submit" disabled={save.isPending}>
            {bucket ? 'Save' : 'Make bucket'}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  )
}
