import { Banknote, Pencil, PieChart, Plus, Trash2, Wallet } from 'lucide-react'
import { useState, type ComponentProps } from 'react'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'

import { useBuckets, useDeleteBucket, type Bucket } from '@/api/queries'
import { Table, TBody, Td, Th, THead, Tr } from '@/components/DataTable'
import { EmptyState } from '@/components/EmptyState'
import { ErrorText } from '@/components/Field'
import { InfoTip } from '@/components/InfoTip'
import { Loading } from '@/components/Loading'
import { RowActions } from '@/components/RowActions'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog } from '@/components/ui/dialog'
import { useConfirm } from '@/hooks/use-confirm'
import { bucketPath, investPath } from '@/lib/buckets'
import { modelPath } from '@/lib/models'
import { inr } from '@/lib/money'
import { toneClass } from '@/lib/percent'

import { BucketDialog } from './BucketDialog'

/** A button that opens the New bucket dialog. */
export function NewBucketButton({
  onMade,
  children = (
    <>
      <Plus /> New bucket
    </>
  ),
  ...props
}: { onMade?: (bucket: Bucket) => void } & ComponentProps<typeof Button>) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <Button {...props} onClick={() => setOpen(true)}>
        {children}
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        {open && (
          <BucketDialog
            onDone={(made) => {
              setOpen(false)
              if (made) onMade?.(made)
            }}
          />
        )}
      </Dialog>
    </>
  )
}

/** A button that opens the bucket's Edit dialog, e.g. to choose its model. */
export function EditBucketButton({
  bucket,
  children,
  ...props
}: { bucket: Bucket } & ComponentProps<typeof Button>) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <Button {...props} onClick={() => setOpen(true)}>
        {children}
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        {open && <BucketDialog bucket={bucket} onDone={() => setOpen(false)} />}
      </Dialog>
    </>
  )
}

/** Every bucket with what it holds; a row opens the bucket's funds. */
export function Buckets() {
  const buckets = useBuckets()
  const remove = useDeleteBucket()
  const confirm = useConfirm()
  const navigate = useNavigate()
  const [editing, setEditing] = useState<Bucket | null>(null)

  async function onDelete(bucket: Bucket) {
    const yes = await confirm({
      title: `Delete ${bucket.name}?`,
      description: bucket.paper
        ? 'Its paper purchases are deleted too.'
        : 'Its purchases stay, in no bucket.',
    })
    if (!yes) return
    remove.mutate(bucket.id, { onSuccess: () => toast.success(`${bucket.name} deleted`) })
  }

  if (buckets.isPending) return <Loading />
  if (buckets.isError) return <ErrorText error={buckets.error} />
  if (buckets.data.length === 0) {
    return (
      <EmptyState
        icon={Wallet}
        title="No buckets yet"
        action={<NewBucketButton onMade={(made) => navigate(bucketPath(made.id))} />}
      />
    )
  }

  return (
    <section className="flex flex-col gap-3">
      <Table label="Buckets">
        <THead>
          <Th>Bucket</Th>
          <Th>Model</Th>
          <Th numeric>Value</Th>
          <Th numeric>Gain</Th>
          <Th numeric>
            <span className="inline-flex items-center gap-1">
              vs model
              <InfoTip label="vs model">
                Gain minus the same purchases and sales split by the model&apos;s weights.
              </InfoTip>
            </span>
          </Th>
          <Th />
        </THead>
        <TBody>
          {buckets.data.map((bucket) => (
            <Tr key={bucket.id} to={bucketPath(bucket.id)}>
              <Td>
                <span className="flex items-center gap-2 font-medium">
                  {bucket.name}
                  {bucket.paper && <Badge variant="outline">Paper</Badge>}
                </span>
                <span className="text-muted-foreground text-xs">
                  {bucket.purchases === 1 ? '1 purchase' : `${bucket.purchases} purchases`}
                </span>
              </Td>
              <Td className="text-muted-foreground">{bucket.model?.name ?? '—'}</Td>
              <Td numeric>{bucket.value ? inr(bucket.value) : '—'}</Td>
              <Td numeric className={toneClass(bucket.gain)}>
                {bucket.gain ? inr(bucket.gain) : '—'}
              </Td>
              <Td numeric className={toneClass(bucket.ahead_of_model)}>
                {bucket.ahead_of_model ? inr(bucket.ahead_of_model) : '—'}
              </Td>
              <Td className="w-0">
                <RowActions
                  label={`Actions for ${bucket.name}`}
                  actions={[
                    {
                      label: 'Invest',
                      icon: Banknote,
                      hidden: !bucket.model,
                      onSelect: () => navigate(investPath(bucket.id)),
                    },
                    {
                      label: 'Open model',
                      icon: PieChart,
                      hidden: !bucket.model,
                      onSelect: () => bucket.model && navigate(modelPath(bucket.model.id)),
                    },
                    { label: 'Edit', icon: Pencil, onSelect: () => setEditing(bucket) },
                    {
                      label: 'Delete',
                      icon: Trash2,
                      destructive: true,
                      onSelect: () => void onDelete(bucket),
                    },
                  ]}
                />
              </Td>
            </Tr>
          ))}
        </TBody>
      </Table>
      <div>
        <NewBucketButton variant="outline" />
      </div>
      <ErrorText error={remove.error} />
      <Dialog open={editing !== null} onOpenChange={(open) => !open && setEditing(null)}>
        {editing && (
          <BucketDialog key={editing.id} bucket={editing} onDone={() => setEditing(null)} />
        )}
      </Dialog>
    </section>
  )
}
