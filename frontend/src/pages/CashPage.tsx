import { Loader2, Pencil, Plus, Trash2, X } from 'lucide-react'
import { useId, useState, type FormEvent, type ReactNode } from 'react'
import { Link } from 'react-router'

import {
  useBuckets,
  useCash,
  useCashPlan,
  useDeleteCashAccount,
  usePlanSettings,
  useSaveCashAccount,
  useSavePlanSettings,
  type Cash,
  type CashAccount,
  type CashPlan,
  type PlanSettings,
} from '@/api/queries'
import { InstrumentSearch } from '@/components/InstrumentSearch'
import { Stat, StatGrid } from '@/components/Stat'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { NativeSelect } from '@/components/ui/native-select'
import { planLabel } from '@/lib/instruments'
import { inr } from '@/lib/money'
import { formatPercent } from '@/lib/percent'
import { formatDate, formatDateTime, formatMonthYear } from '@/lib/time'

type Earmark = CashAccount['earmark']

const EARMARK_LABELS: Record<Earmark, string> = {
  emergency: 'Emergency',
  deployable: 'Deployable',
  reserved: 'Reserved',
}

const EARMARK_HINTS: Record<Earmark, string> = {
  emergency: 'Never invested by the plan.',
  deployable: 'Free to invest: the plan uses it by default.',
  reserved: 'Set aside for something known; not invested.',
}

/** Is a decimal string from the API above zero? Checked on the string, no arithmetic. */
function positive(amount: string): boolean {
  return !amount.startsWith('-') && /[1-9]/.test(amount)
}

export function CashPage() {
  const cash = useCash()
  const settings = usePlanSettings()

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Cash</h1>
        <p className="text-muted-foreground mt-1">
          Your INR cash, the emergency money kept apart, and where new cash should go so your funds
          move towards your target split without selling. Plain arithmetic, no AI.
        </p>
      </div>

      {cash.isError && <p className="text-destructive text-sm">{cash.error.message}</p>}
      {cash.isSuccess && <CashSummary cash={cash.data} />}
      {settings.isSuccess && cash.isSuccess && (
        <PlanCard settings={settings.data} deployable={cash.data.deployable} />
      )}
      {cash.isSuccess && <Accounts accounts={cash.data.accounts} />}
      {settings.isError && <p className="text-destructive text-sm">{settings.error.message}</p>}
      {settings.isSuccess && <SettingsCard settings={settings.data} />}
    </div>
  )
}

function CashSummary({ cash }: { cash: Cash }) {
  const emergency = cash.emergency
  const short = positive(emergency.shortfall)
  return (
    <StatGrid>
      <Stat label="Deployable" value={inr(cash.deployable)} hint="Free to invest" />
      <Stat label="Reserved" value={inr(cash.reserved)} hint="Set aside, not invested" />
      <Stat
        label="Emergency money"
        value={inr(emergency.total)}
        hint={
          emergency.fund
            ? `${inr(emergency.cash)} cash + ${inr(emergency.fund.value)} in fund`
            : 'Emergency-earmarked cash'
        }
      />
      <Stat
        label="Emergency goal"
        value={inr(emergency.goal)}
        hint={short ? `Short by ${inr(emergency.shortfall)}` : 'Met'}
        tone={short ? 'negative' : undefined}
      />
    </StatGrid>
  )
}

function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: (id: string) => ReactNode
}) {
  const id = useId()
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      {children(id)}
      {hint && <p className="text-muted-foreground text-xs">{hint}</p>}
    </div>
  )
}

// The plan ---------------------------------------------------------------------------------

function PlanCard({ settings, deployable }: { settings: PlanSettings; deployable: string }) {
  const [amount, setAmount] = useState('')
  const [asked, setAsked] = useState<string | null>(null)
  const plan = useCashPlan(asked)

  function submit(event: FormEvent) {
    event.preventDefault()
    const next = amount.trim()
    // The same amount again still asks again: cash or NAVs may have changed since.
    if (next === asked) void plan.refetch()
    else setAsked(next)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>I have ₹X: where does it go?</CardTitle>
        <CardDescription>
          {settings.target_bucket ? (
            <>
              Target split: <strong>{settings.target_bucket.name}</strong>. Emergency money is
              topped up first, then the funds furthest below target get the rest, in whole rupees.
            </>
          ) : (
            'Choose which bucket is your target split in the settings below first.'
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <form aria-label="Make a plan" className="flex flex-wrap items-end gap-2" onSubmit={submit}>
          <div className="min-w-56 flex-1">
            <Field label="Amount (₹)" hint={`Blank: all deployable cash, ${inr(deployable)}.`}>
              {(id) => (
                <Input
                  id={id}
                  inputMode="decimal"
                  value={amount}
                  onChange={(event) => setAmount(event.target.value)}
                />
              )}
            </Field>
          </div>
          <Button type="submit" className="mb-5" disabled={!settings.target_bucket}>
            {plan.isFetching && <Loader2 className="animate-spin" />}
            Make plan
          </Button>
        </form>
        {plan.isError && (
          <p role="alert" className="text-destructive text-sm">
            {plan.error.message}
          </p>
        )}
        {plan.isSuccess && <PlanResult plan={plan.data} />}
      </CardContent>
    </Card>
  )
}

function PlanResult({ plan }: { plan: CashPlan }) {
  const emergencyFund = plan.emergency.fund?.fund
  return (
    <div className="flex flex-col gap-4">
      <StatGrid>
        <Stat label="Amount" value={inr(plan.amount)} />
        <Stat
          label="Emergency top-up"
          value={inr(plan.emergency_topup)}
          hint={
            positive(plan.emergency_topup)
              ? emergencyFund
                ? `Into ${emergencyFund.name}`
                : 'Keep as emergency cash'
              : positive(plan.emergency.shortfall)
                ? undefined
                : 'Goal already met'
          }
        />
        <Stat label="Into funds" value={inr(plan.invested)} hint={plan.bucket.name} />
        <Stat
          label="Left as cash"
          value={inr(plan.left)}
          hint={
            positive(plan.left) ? `Under ${inr(plan.min_per_fund)} a fund, or paise` : undefined
          }
        />
      </StatGrid>

      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm" aria-label="Plan per fund">
          <thead className="bg-muted/50 text-muted-foreground text-left text-xs">
            <tr>
              <th className="px-3 py-2 font-medium">Fund</th>
              <th className="px-3 py-2 text-right font-medium">Target</th>
              <th className="px-3 py-2 text-right font-medium">Value now</th>
              <th className="px-3 py-2 text-right font-medium">Share now</th>
              <th className="px-3 py-2 text-right font-medium">Invest</th>
              <th className="px-3 py-2 text-right font-medium">Share after</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {plan.funds.map((row) => (
              <tr key={row.fund.id}>
                <td className="px-3 py-2">
                  <div className="font-medium">{row.fund.name}</div>
                  <div className="text-muted-foreground text-xs">
                    AMFI {row.fund.amfi_code}
                    {planLabel(row.fund) && ` · ${planLabel(row.fund)}`}
                    {row.nav_date && ` · NAV of ${formatDate(row.nav_date)}`}
                  </div>
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {formatPercent(row.weight, { sign: false })}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">{inr(row.value_now)}</td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {formatPercent(row.share_now, { sign: false })}
                </td>
                <td className="px-3 py-2 text-right font-semibold tabular-nums">
                  {positive(row.invest) ? inr(row.invest) : '—'}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {formatPercent(row.share_after, { sign: false })}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot className="border-t text-xs">
            <tr>
              <td className="text-muted-foreground px-3 py-2">Bucket total</td>
              <td />
              <td className="px-3 py-2 text-right tabular-nums">{inr(plan.value_now)}</td>
              <td />
              <td className="px-3 py-2 text-right tabular-nums">{inr(plan.invested)}</td>
              <td className="px-3 py-2 text-right tabular-nums">{inr(plan.value_after)}</td>
            </tr>
          </tfoot>
        </table>
      </div>

      {plan.months.length > 0 && <StaggerTable plan={plan} />}

      {plan.ignored.length > 0 && (
        <p className="text-muted-foreground text-xs">
          Not part of the plan (outside your target split):{' '}
          {plan.ignored.map((row) => `${row.fund.name} (${inr(row.value)})`).join(', ')}.
        </p>
      )}
    </div>
  )
}

function StaggerTable({ plan }: { plan: CashPlan }) {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm">
        <strong>Stagger it:</strong> {inr(plan.to_funds)} is above your threshold, so park it in{' '}
        {plan.stagger_fund ? plan.stagger_fund.name : 'a liquid or arbitrage fund'} and move it in{' '}
        {plan.months.length} monthly transfers (an STP):
      </p>
      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full text-sm" aria-label="Monthly transfers">
          <thead className="bg-muted/50 text-muted-foreground text-left text-xs">
            <tr>
              <th className="px-3 py-2 font-medium">Month</th>
              {plan.funds.map((row) => (
                <th key={row.fund.id} className="px-3 py-2 text-right font-medium">
                  {row.fund.name}
                </th>
              ))}
              <th className="px-3 py-2 text-right font-medium">Total</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {plan.months.map((month) => (
              <tr key={month.month}>
                <td className="px-3 py-2">{formatMonthYear(month.month)}</td>
                {month.amounts.map((amount, i) => (
                  <td key={plan.funds[i].fund.id} className="px-3 py-2 text-right tabular-nums">
                    {positive(amount) ? inr(amount) : '—'}
                  </td>
                ))}
                <td className="px-3 py-2 text-right font-medium tabular-nums">
                  {inr(month.total)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// Accounts ---------------------------------------------------------------------------------

function Accounts({ accounts }: { accounts: CashAccount[] }) {
  const [editing, setEditing] = useState<CashAccount | 'new' | null>(null)
  const remove = useDeleteCashAccount()

  return (
    <Card>
      <CardHeader>
        <CardTitle>Cash accounts</CardTitle>
        <CardDescription>Current balances only. Update them when they change.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {accounts.length > 0 && (
          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full text-sm" aria-label="Cash accounts">
              <thead className="bg-muted/50 text-muted-foreground text-left text-xs">
                <tr>
                  <th className="px-3 py-2 font-medium">Account</th>
                  <th className="px-3 py-2 font-medium">Earmark</th>
                  <th className="px-3 py-2 text-right font-medium">Balance</th>
                  <th className="px-3 py-2 text-right font-medium">Updated</th>
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody className="divide-y">
                {accounts.map((account) => (
                  <tr key={account.id}>
                    <td className="px-3 py-2">
                      <div className="font-medium">{account.name}</div>
                      {account.note && (
                        <div className="text-muted-foreground text-xs">{account.note}</div>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <Badge variant={account.earmark === 'deployable' ? 'default' : 'secondary'}>
                        {EARMARK_LABELS[account.earmark]}
                      </Badge>
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">{inr(account.balance)}</td>
                    <td className="text-muted-foreground px-3 py-2 text-right text-xs">
                      {formatDateTime(account.updated_at)}
                    </td>
                    <td className="px-3 py-2 text-right whitespace-nowrap">
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Edit ${account.name}`}
                        onClick={() => setEditing(account)}
                      >
                        <Pencil />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Delete ${account.name}`}
                        onClick={() => {
                          if (window.confirm(`Delete the account ${account.name}?`))
                            remove.mutate(account.id)
                        }}
                      >
                        <Trash2 />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {remove.isError && <p className="text-destructive text-sm">{remove.error.message}</p>}
        {editing ? (
          <AccountForm
            key={editing === 'new' ? 'new' : editing.id}
            account={editing === 'new' ? undefined : editing}
            onDone={() => setEditing(null)}
          />
        ) : (
          <div>
            <Button variant="outline" onClick={() => setEditing('new')}>
              <Plus /> Add account
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function AccountForm({ account, onDone }: { account?: CashAccount; onDone: () => void }) {
  const save = useSaveCashAccount()
  const [draft, setDraft] = useState({
    name: account?.name ?? '',
    balance: account?.balance ?? '',
    earmark: account?.earmark ?? ('deployable' as Earmark),
    note: account?.note ?? '',
  })

  function submit(event: FormEvent) {
    event.preventDefault()
    save.mutate(
      {
        id: account?.id,
        body: { ...draft, balance: draft.balance.trim(), note: draft.note || null },
      },
      { onSuccess: onDone },
    )
  }

  return (
    <form
      aria-label={account ? `Edit ${account.name}` : 'Add account'}
      className="border-primary/40 flex flex-col gap-4 rounded-lg border p-4"
      onSubmit={submit}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Name">
          {(id) => (
            <Input
              id={id}
              required
              value={draft.name}
              onChange={(event) => setDraft({ ...draft, name: event.target.value })}
            />
          )}
        </Field>
        <Field label="Balance (₹)">
          {(id) => (
            <Input
              id={id}
              inputMode="decimal"
              required
              value={draft.balance}
              onChange={(event) => setDraft({ ...draft, balance: event.target.value })}
            />
          )}
        </Field>
        <Field label="Earmark" hint={EARMARK_HINTS[draft.earmark]}>
          {(id) => (
            <NativeSelect
              id={id}
              value={draft.earmark}
              onChange={(event) => setDraft({ ...draft, earmark: event.target.value as Earmark })}
            >
              {Object.entries(EARMARK_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </NativeSelect>
          )}
        </Field>
        <Field label="Note (optional)">
          {(id) => (
            <Input
              id={id}
              value={draft.note}
              onChange={(event) => setDraft({ ...draft, note: event.target.value })}
            />
          )}
        </Field>
      </div>
      {save.isError && (
        <p role="alert" className="text-destructive text-sm">
          {save.error.message}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" disabled={save.isPending}>
          {save.isPending && <Loader2 className="animate-spin" />}
          {account ? 'Save' : 'Add account'}
        </Button>
      </div>
    </form>
  )
}

// Settings ---------------------------------------------------------------------------------

type FundChoice = { id: number; name: string } | null

function SettingsCard({ settings }: { settings: PlanSettings }) {
  const [editing, setEditing] = useState(false)
  const fund = (value: PlanSettings['emergency_fund']) =>
    value ? `${value.name}${planLabel(value) ? ` · ${planLabel(value)}` : ''}` : 'None'

  return (
    <Card>
      <CardHeader>
        <CardTitle>Plan settings</CardTitle>
        <CardDescription>The rules the plan follows.</CardDescription>
      </CardHeader>
      <CardContent>
        {editing ? (
          <SettingsForm settings={settings} onDone={() => setEditing(false)} />
        ) : (
          <div className="flex flex-col gap-4">
            <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
              <Setting label="Target split">
                {settings.target_bucket ? (
                  <Link to="/buckets" className="underline-offset-4 hover:underline">
                    {settings.target_bucket.name}
                  </Link>
                ) : (
                  'Not chosen'
                )}
              </Setting>
              <Setting label="Emergency goal">{inr(settings.emergency_goal)}</Setting>
              <Setting label="Emergency fund">{fund(settings.emergency_fund)}</Setting>
              <Setting label="Minimum per fund">{inr(settings.min_per_fund)}</Setting>
              <Setting label="Stagger from">
                {settings.stagger_threshold
                  ? `${inr(settings.stagger_threshold)}, over ${settings.stagger_months} months`
                  : 'Never'}
              </Setting>
              <Setting label="Stagger through">{fund(settings.stagger_fund)}</Setting>
            </dl>
            <div>
              <Button variant="outline" onClick={() => setEditing(true)}>
                <Pencil /> Change settings
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function Setting({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-muted-foreground text-xs">{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}

function FundPicker({
  label,
  hint,
  value,
  onChange,
}: {
  label: string
  hint: string
  value: FundChoice
  onChange: (value: FundChoice) => void
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-sm font-medium">{label}</span>
      {value ? (
        <div className="flex items-center gap-2 text-sm">
          <span className="min-w-0 flex-1 truncate">{value.name}</span>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label={`Clear ${label.toLowerCase()}`}
            onClick={() => onChange(null)}
          >
            <X />
          </Button>
        </div>
      ) : (
        <InstrumentSearch
          kind="mutual_fund"
          label={label}
          placeholder="Fund name or AMFI scheme code"
          onSelect={(instrument) => onChange({ id: instrument.id, name: instrument.name })}
        />
      )}
      <p className="text-muted-foreground text-xs">{hint}</p>
    </div>
  )
}

function SettingsForm({ settings, onDone }: { settings: PlanSettings; onDone: () => void }) {
  const buckets = useBuckets()
  const save = useSavePlanSettings()
  const [draft, setDraft] = useState({
    target_bucket_id: settings.target_bucket ? String(settings.target_bucket.id) : '',
    emergency_goal: settings.emergency_goal,
    stagger_threshold: settings.stagger_threshold ?? '',
    stagger_months: String(settings.stagger_months),
    min_per_fund: settings.min_per_fund,
  })
  const [emergencyFund, setEmergencyFund] = useState<FundChoice>(settings.emergency_fund)
  const [staggerFund, setStaggerFund] = useState<FundChoice>(settings.stagger_fund)

  function submit(event: FormEvent) {
    event.preventDefault()
    save.mutate(
      {
        target_bucket_id: draft.target_bucket_id ? Number(draft.target_bucket_id) : null,
        emergency_goal: draft.emergency_goal.trim(),
        emergency_fund_id: emergencyFund?.id ?? null,
        stagger_fund_id: staggerFund?.id ?? null,
        stagger_threshold: draft.stagger_threshold.trim() || null,
        stagger_months: Number(draft.stagger_months),
        min_per_fund: draft.min_per_fund.trim(),
      },
      { onSuccess: onDone },
    )
  }

  return (
    <form aria-label="Plan settings" className="flex flex-col gap-4" onSubmit={submit}>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Target split" hint="The bucket new cash should move you towards.">
          {(id) => (
            <NativeSelect
              id={id}
              value={draft.target_bucket_id}
              onChange={(event) => setDraft({ ...draft, target_bucket_id: event.target.value })}
            >
              <option value="">Not chosen</option>
              {buckets.data?.map((bucket) => (
                <option key={bucket.id} value={bucket.id}>
                  {bucket.name}
                </option>
              ))}
            </NativeSelect>
          )}
        </Field>
        <Field label="Emergency goal (₹)" hint="Topped up before anything is invested.">
          {(id) => (
            <Input
              id={id}
              inputMode="decimal"
              required
              value={draft.emergency_goal}
              onChange={(event) => setDraft({ ...draft, emergency_goal: event.target.value })}
            />
          )}
        </Field>
        <FundPicker
          label="Emergency fund"
          hint="A liquid or arbitrage fund holding emergency money: it counts towards the goal and is never in the split."
          value={emergencyFund}
          onChange={setEmergencyFund}
        />
        <FundPicker
          label="Stagger through"
          hint="The liquid or arbitrage fund large amounts wait in before monthly transfers."
          value={staggerFund}
          onChange={setStaggerFund}
        />
        <Field label="Stagger from (₹)" hint="Blank: never stagger.">
          {(id) => (
            <Input
              id={id}
              inputMode="decimal"
              value={draft.stagger_threshold}
              onChange={(event) => setDraft({ ...draft, stagger_threshold: event.target.value })}
            />
          )}
        </Field>
        <Field label="Stagger over (months)" hint="2 to 24.">
          {(id) => (
            <Input
              id={id}
              type="number"
              min={2}
              max={24}
              required
              value={draft.stagger_months}
              onChange={(event) => setDraft({ ...draft, stagger_months: event.target.value })}
            />
          )}
        </Field>
        <Field
          label="Minimum per fund (₹)"
          hint="A fund whose share would be smaller gets nothing; the others share it."
        >
          {(id) => (
            <Input
              id={id}
              inputMode="decimal"
              required
              value={draft.min_per_fund}
              onChange={(event) => setDraft({ ...draft, min_per_fund: event.target.value })}
            />
          )}
        </Field>
      </div>
      {save.isError && (
        <p role="alert" className="text-destructive text-sm">
          {save.error.message}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" disabled={save.isPending}>
          {save.isPending && <Loader2 className="animate-spin" />}
          Save settings
        </Button>
      </div>
    </form>
  )
}
