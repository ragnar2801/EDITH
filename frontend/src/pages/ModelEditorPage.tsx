import { useNavigate, useParams } from 'react-router'

import { useBuckets, useDefaultBenchmark } from '@/api/queries'
import { ErrorText } from '@/components/Field'
import { Loading } from '@/components/Loading'
import { ModelEditor } from '@/components/models/ModelEditor'
import { PageHeader } from '@/components/PageHeader'
import { MODELS_PATH, backtestPath, draftOf, modelPath, newDraft } from '@/lib/models'

/** New model, or edit one: a page of its own. */
export function ModelEditorPage() {
  const params = useParams()
  const id = params.id ? Number(params.id) : null
  const navigate = useNavigate()
  const buckets = useBuckets()
  const benchmark = useDefaultBenchmark()
  const bucket = id === null ? null : buckets.data?.find((b) => b.id === id)

  const back = bucket
    ? { to: modelPath(bucket.id), label: bucket.name }
    : { to: MODELS_PATH, label: 'Models' }
  if (buckets.isError) return <ErrorText error={buckets.error} />
  if ((id === null && benchmark.isPending) || (id !== null && buckets.isPending)) {
    return <Loading />
  }
  if (id !== null && !bucket) {
    return <PageHeader back={back} title="Model not found" />
  }

  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <PageHeader back={back} title={bucket ? `Edit ${bucket.name}` : 'New model'} />
      <ModelEditor
        initial={bucket ? draftOf(bucket) : newDraft(benchmark.data ?? null)}
        onSaved={(saved) => navigate(bucket ? modelPath(saved.id) : backtestPath(saved.id))}
        onCancel={() => navigate(back.to)}
      />
    </div>
  )
}
