import { useNavigate, useParams } from 'react-router'

import { useModels, useDefaultBenchmark } from '@/api/queries'
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
  const models = useModels()
  const benchmark = useDefaultBenchmark()
  const model = id === null ? null : models.data?.find((b) => b.id === id)

  const back = model
    ? { to: modelPath(model.id), label: model.name }
    : { to: MODELS_PATH, label: 'Models' }
  if (models.isError) return <ErrorText error={models.error} />
  if ((id === null && benchmark.isPending) || (id !== null && models.isPending)) {
    return <Loading />
  }
  if (id !== null && !model) {
    return <PageHeader back={back} title="Model not found" />
  }

  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <PageHeader back={back} title={model ? `Edit ${model.name}` : 'New model'} />
      <ModelEditor
        initial={model ? draftOf(model) : newDraft(benchmark.data ?? null)}
        onSaved={(saved) => navigate(model ? modelPath(saved.id) : backtestPath(saved.id))}
        onCancel={() => navigate(back.to)}
      />
    </div>
  )
}
