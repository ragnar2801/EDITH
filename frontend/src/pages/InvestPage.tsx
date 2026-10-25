import { Settings2 } from 'lucide-react'
import { Link } from 'react-router'

import { useCash, usePlanSettings } from '@/api/queries'
import { CashPlan } from '@/components/cash/CashPlan'
import { ErrorText } from '@/components/Field'
import { InfoTip } from '@/components/InfoTip'
import { Loading } from '@/components/Loading'
import { PageHeader } from '@/components/PageHeader'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { MODELS_PATH, modelPath } from '@/lib/models'

/** I have ₹X: what do I buy? One job (J5). */
export function InvestPage() {
  const cash = useCash()
  const settings = usePlanSettings()
  const target = settings.data?.target_bucket

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Invest"
        meta={
          target && (
            <span className="flex items-center gap-1.5">
              Target
              <Badge asChild variant="outline">
                <Link to={modelPath(target.id)}>{target.name}</Link>
              </Badge>
              <InfoTip label="Target">The model new cash moves you towards.</InfoTip>
            </span>
          )
        }
        actions={
          <Button asChild variant="outline" size="sm">
            <Link to="/settings">
              <Settings2 /> Rules
            </Link>
          </Button>
        }
      />
      <ErrorText error={cash.error ?? settings.error} />
      {(cash.isPending || settings.isPending) && <Loading />}
      {cash.isSuccess && settings.isSuccess && (
        <CashPlan
          investable={cash.data.deployable}
          ready={!!target}
          chooseTarget={
            <Button asChild>
              <Link to={MODELS_PATH}>Choose</Link>
            </Button>
          }
        />
      )}
    </div>
  )
}
