import { Pencil } from 'lucide-react'
import { useState } from 'react'

import { useCash, usePlanSettings } from '@/api/queries'
import { CashAccounts } from '@/components/cash/CashAccounts'
import { CashPlan } from '@/components/cash/CashPlan'
import { CashSummary } from '@/components/cash/CashSummary'
import { InvestRulesForm, InvestRulesSummary } from '@/components/cash/InvestRules'
import { ErrorText } from '@/components/Field'
import { Loading } from '@/components/Loading'
import { PageHeader } from '@/components/PageHeader'
import { Section } from '@/components/Section'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

export function CashPage() {
  const cash = useCash()
  const settings = usePlanSettings()
  const [editingRules, setEditingRules] = useState(false)

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-8">
      <PageHeader title="Cash" />
      <ErrorText error={cash.error ?? settings.error} />
      {(cash.isPending || settings.isPending) && <Loading />}
      {cash.isSuccess && <CashSummary cash={cash.data} />}
      {settings.isSuccess && cash.isSuccess && (
        <Section title="Invest">
          <CashPlan
            investable={cash.data.deployable}
            ready={!!settings.data.target_bucket}
            chooseTarget={<Button onClick={() => setEditingRules(true)}>Choose</Button>}
          />
        </Section>
      )}
      {cash.isSuccess && (
        <Section title="Accounts">
          <CashAccounts accounts={cash.data.accounts} />
        </Section>
      )}
      {settings.isSuccess && (
        <Section
          title="Invest rules"
          actions={
            <Button variant="outline" size="sm" onClick={() => setEditingRules(true)}>
              <Pencil /> Edit
            </Button>
          }
        >
          <InvestRulesSummary settings={settings.data} />
          <Dialog open={editingRules} onOpenChange={setEditingRules}>
            <DialogContent className="sm:max-w-2xl">
              <DialogHeader>
                <DialogTitle>Invest rules</DialogTitle>
                <DialogDescription className="sr-only">
                  Target model, emergency money and staggering
                </DialogDescription>
              </DialogHeader>
              <InvestRulesForm settings={settings.data} onDone={() => setEditingRules(false)} />
            </DialogContent>
          </Dialog>
        </Section>
      )}
    </div>
  )
}
