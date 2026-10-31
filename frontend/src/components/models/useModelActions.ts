import { useNavigate } from 'react-router'
import { toast } from 'sonner'

import { useDeleteModel, useDuplicateModel } from '@/api/queries'
import { useConfirm } from '@/hooks/use-confirm'
import { modelPath, type Model } from '@/lib/models'

/** Duplicate and delete, with their toasts and confirm, for a list row or a model page. */
export function useModelActions() {
  const duplicate = useDuplicateModel()
  const remove = useDeleteModel()
  const confirm = useConfirm()
  const navigate = useNavigate()

  return {
    error: duplicate.error ?? remove.error,
    // The copy opens in the editor, so it can be renamed and changed straight away.
    duplicate: (model: Model) =>
      duplicate.mutate(model.id, {
        onSuccess: (copy) => {
          toast.success(`Copied ${model.name} to ${copy.name}`)
          navigate(modelPath(copy.id, 'edit'))
        },
      }),
    remove: async (model: Model, then?: string) => {
      const yes = await confirm({
        title: `Delete ${model.name}?`,
        description: 'Its saved backtests are deleted too. Buckets following it keep their funds.',
      })
      if (!yes) return
      remove.mutate(model.id, {
        onSuccess: () => {
          toast.success(`${model.name} deleted`)
          if (then) navigate(then)
        },
      })
    },
  }
}
