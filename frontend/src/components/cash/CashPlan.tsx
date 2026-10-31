import { Loader2, Target } from 'lucide-react'
import { useState, type FormEvent, type ReactNode } from 'react'

import { useCashPlan, type CashPlan as Plan } from '@/api/queries'
import { Table, TBody, Td, TFoot, Th, THead, Tr } from '@/components/DataTable'
import { EmptyState } from '@/components/EmptyState'
import { ErrorText, Field } from '@/components/Field'
import { InfoTip } from '@/components/InfoTip'
import { Stat, StatGrid } from '@/components/Stat'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { fundPath, planLabel } from '@/lib/instruments'
import { inr } from '@/lib/money'
import { formatPercent } from '@/lib/percent'
import { formatDate, formatMonthYear } from '@/lib/time'

import { positive } from './labels'

/** "I have ₹X": one amount in, what to buy out. */
export function CashPlan({
  investable,
  ready,
  chooseTarget,
}: {
  investable: string
  /** A target model is chosen; without one there's nothing to plan towards. */
  ready: boolean
  chooseTarget: ReactNode
}) {
  const [amount, setAmount] = useState(positive(investable) ? investable : '')
  const [asked, setAsked] = useState<string | null>(null)
  const plan = useCashPlan(asked)

  function submit(event: FormEvent) {
    event.preventDefault()
    const next = amount.trim()
    // The same amount again still asks again: cash or NAVs may have changed since.
    if (next === asked) void plan.refetch()
    else setAsked(next)
  }

  if (!ready)
    return <EmptyState icon={Target} title="Choose a target model" action={chooseTarget} />

  return (
    <div className="flex flex-col gap-6">
      <form aria-label="Make a plan" className="flex flex-wrap items-end gap-2" onSubmit={submit}>
        <Field label="Amount (₹)" className="w-full max-w-xs">
          {(id) => (
            <Input
              id={id}
              inputMode="decimal"
              placeholder="1,00,000"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
            />
          )}
        </Field>
        <Button type="submit">
          {plan.isFetching && <Loader2 className="animate-spin" />}
          Make plan
        </Button>
      </form>
      <ErrorText error={plan.error} />
      {plan.isSuccess && <PlanResult plan={plan.data} />}
    </div>
  )
}

function PlanResult({ plan }: { plan: Plan }) {
  const emergencyFund = plan.emergency.fund?.fund
  return (
    <div className="flex flex-col gap-6">
      <StatGrid>
        <Stat label="Amount" value={inr(plan.amount)} />
        <Stat
          label="Emergency top-up"
          info={
            <InfoTip label="Emergency top-up">Brings emergency money up to its goal first.</InfoTip>
          }
          value={inr(plan.emergency_topup)}
          hint={
            positive(plan.emergency_topup)
              ? emergencyFund
                ? `Into ${emergencyFund.name}`
                : 'Keep as cash'
              : undefined
          }
        />
        <Stat label="Into funds" value={inr(plan.invested)} hint={plan.bucket.name} />
        <Stat
          label="Left as cash"
          info={
            <InfoTip label="Left as cash">
              Shares under {inr(plan.min_per_fund)} a fund, and paise.
            </InfoTip>
          }
          value={inr(plan.left)}
        />
      </StatGrid>

      <Table label="Plan per fund">
        <THead>
          <Th>Fund</Th>
          <Th numeric>Target</Th>
          <Th numeric>Value now</Th>
          <Th numeric>Share now</Th>
          <Th numeric>Buy</Th>
          <Th numeric>Share after</Th>
        </THead>
        <TBody>
          {plan.funds.map((row) => (
            <Tr key={row.fund.id} to={fundPath(row.fund.id)}>
              <Td>
                <div className="font-medium">{row.fund.name}</div>
                <div className="text-muted-foreground text-xs">
                  {[planLabel(row.fund), row.nav_date && `NAV of ${formatDate(row.nav_date)}`]
                    .filter(Boolean)
                    .join(' · ')}
                </div>
              </Td>
              <Td numeric>{formatPercent(row.weight, { sign: false })}</Td>
              <Td numeric>{inr(row.value_now)}</Td>
              <Td numeric>{formatPercent(row.share_now, { sign: false })}</Td>
              <Td numeric className="font-semibold">
                {positive(row.invest) ? inr(row.invest) : '—'}
              </Td>
              <Td numeric>{formatPercent(row.share_after, { sign: false })}</Td>
            </Tr>
          ))}
        </TBody>
        <TFoot>
          <Td className="text-muted-foreground">Total</Td>
          <Td />
          <Td numeric>{inr(plan.value_now)}</Td>
          <Td />
          <Td numeric>{inr(plan.invested)}</Td>
          <Td numeric>{inr(plan.value_after)}</Td>
        </TFoot>
      </Table>

      {plan.months.length > 0 && <StaggerTable plan={plan} />}

      {plan.ignored.length > 0 && (
        <section className="flex flex-col gap-1 text-sm">
          <h2 className="text-muted-foreground flex items-center gap-1 text-xs font-medium">
            Not in the target model
            <InfoTip label="Not in the target model">Held, but left out of the plan.</InfoTip>
          </h2>
          <ul>
            {plan.ignored.map((row) => (
              <li key={row.fund.id} className="flex justify-between gap-3 py-0.5">
                <span>{row.fund.name}</span>
                <span className="tabular-nums">{inr(row.value)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}

function StaggerTable({ plan }: { plan: Plan }) {
  return (
    <section className="flex flex-col gap-2">
      <h2 className="flex items-center gap-1.5 text-base font-semibold">
        Monthly transfers
        <InfoTip label="Monthly transfers">
          Above your stagger threshold: park the money, then move it in monthly (an STP).
        </InfoTip>
      </h2>
      <p className="text-muted-foreground text-sm">
        From {plan.stagger_fund ? plan.stagger_fund.name : 'a liquid or arbitrage fund'} ·{' '}
        {plan.months.length} months
      </p>
      <Table label="Monthly transfers">
        <THead>
          <Th>Month</Th>
          {plan.funds.map((row) => (
            <Th key={row.fund.id} numeric>
              {row.fund.name}
            </Th>
          ))}
          <Th numeric>Total</Th>
        </THead>
        <TBody>
          {plan.months.map((month) => (
            <Tr key={month.month}>
              <Td>{formatMonthYear(month.month)}</Td>
              {month.amounts.map((amount, i) => (
                <Td key={plan.funds[i].fund.id} numeric>
                  {positive(amount) ? inr(amount) : '—'}
                </Td>
              ))}
              <Td numeric className="font-medium">
                {inr(month.total)}
              </Td>
            </Tr>
          ))}
        </TBody>
      </Table>
    </section>
  )
}
