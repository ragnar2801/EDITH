import { useNavigate } from 'react-router'
import { toast } from 'sonner'

import { useDeleteBucket, useDuplicateBucket, useSetTarget } from '@/api/queries'
import { useConfirm } from '@/hooks/use-confirm'
import type { Bucket } from '@/lib/buckets'
import { modelPath } from '@/lib/models'

/** Set as target, duplicate and delete, with their toasts and confirm, for a list row or a model page. */
export function useModelActions() {
  const setTarget = useSetTarget()
  const duplicate = useDuplicateBucket()
  const remove = useDeleteBucket()
  const confirm = useConfirm()
  const navigate = useNavigate()

  return {
    error: setTarget.error ?? duplicate.error ?? remove.error,
    makeTarget: (bucket: Bucket) =>
      setTarget.mutate(bucket.id, {
        onSuccess: () => toast.success(`${bucket.name} is your target`),
      }),
    // The copy opens in the editor, so it can be renamed and changed straight away.
    duplicate: (bucket: Bucket) =>
      duplicate.mutate(bucket.id, {
        onSuccess: (copy) => {
          toast.success(`Copied ${bucket.name} to ${copy.name}`)
          navigate(modelPath(copy.id, 'edit'))
        },
      }),
    remove: async (bucket: Bucket, then?: string) => {
      const yes = await confirm({
        title: `Delete ${bucket.name}?`,
        description: 'Its saved backtests are deleted too.',
      })
      if (!yes) return
      remove.mutate(bucket.id, {
        onSuccess: () => {
          toast.success(`${bucket.name} deleted`)
          if (then) navigate(then)
        },
      })
    },
  }
}
