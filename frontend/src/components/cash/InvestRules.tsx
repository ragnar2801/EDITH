import { X } from 'lucide-react'
import { useState, type FormEvent, type ReactNode } from 'react'
import { toast } from 'sonner'

import { useBuckets, useSavePlanSettings, type PlanSettings } from '@/api/queries'
import { ErrorText, Field } from '@/components/Field'
import { InfoTip } from '@/components/InfoTip'
import { InstrumentSearch } from '@/components/InstrumentSearch'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { NativeSelect } from '@/components/ui/native-select'
import { planLabel } from '@/lib/instruments'
import { inr } from '@/lib/money'

type FundChoice = { id: number; name: string } | null

const RULE_INFO = {
  target: 'The model new cash moves you towards.',
  emergencyGoal: 'Topped up before anything is invested.',
  emergencyFund: 'A liquid or arbitrage fund whose value counts towards the emergency goal.',
  staggerFund: 'Where large amounts wait before the monthly transfers.',
  staggerFrom: 'Amounts this big go in monthly instead of at once. Blank: never.',
  staggerMonths: 'How many monthly transfers, 2 to 24.',
  minPerFund: 'A smaller share gets nothing; the other funds share it.',
}

function fundName(value: PlanSettings['emergency_fund']) {
  return value ? `${value.name}${planLabel(value) ? ` · ${planLabel(value)}` : ''}` : 'None'
}

/** The rules at a glance. */
export function InvestRulesSummary({ settings }: { settings: PlanSettings }) {
  return (
    <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
      <Rule label="Target model" info={RULE_INFO.target}>
        {settings.target_bucket?.name ?? 'Not chosen'}
      </Rule>
      <Rule label="Emergency goal" info={RULE_INFO.emergencyGoal}>
        {inr(settings.emergency_goal)}
      </Rule>
      <Rule label="Emergency fund" info={RULE_INFO.emergencyFund}>
        {fundName(settings.emergency_fund)}
      </Rule>
      <Rule label="Minimum per fund" info={RULE_INFO.minPerFund}>
        {inr(settings.min_per_fund)}
      </Rule>
      <Rule label="Stagger from" info={RULE_INFO.staggerFrom}>
        {settings.stagger_threshold
          ? `${inr(settings.stagger_threshold)} · ${settings.stagger_months} months`
          : 'Never'}
      </Rule>
      <Rule label="Stagger through" info={RULE_INFO.staggerFund}>
        {fundName(settings.stagger_fund)}
      </Rule>
    </dl>
  )
}

function Rule({ label, info, children }: { label: string; info: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-muted-foreground flex items-center gap-1 text-xs">
        {label}
        <InfoTip label={label}>{info}</InfoTip>
      </dt>
      <dd>{children}</dd>
    </div>
  )
}

function FundPicker({
  label,
  info,
  value,
  onChange,
}: {
  label: string
  info: string
  value: FundChoice
  onChange: (value: FundChoice) => void
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="flex items-center gap-1.5 text-sm font-medium">
        {label}
        <InfoTip label={label}>{info}</InfoTip>
      </span>
      {value ? (
        <div className="flex h-9 items-center gap-2 rounded-md border px-3 text-sm">
          <span className="min-w-0 flex-1 truncate">{value.name}</span>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="size-6"
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
          placeholder="Search funds"
          onSelect={(instrument) => onChange({ id: instrument.id, name: instrument.name })}
        />
      )}
    </div>
  )
}

/** Edit the rules; `onDone` runs after a save or a cancel. */
export function InvestRulesForm({
  settings,
  onDone,
}: {
  settings: PlanSettings
  onDone?: () => void
}) {
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
      {
        onSuccess: () => {
          toast.success('Invest rules saved')
          onDone?.()
        },
      },
    )
  }

  return (
    <form aria-label="Invest rules" className="flex flex-col gap-4" onSubmit={submit}>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Target model" info={RULE_INFO.target}>
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
        <Field label="Emergency goal (₹)" info={RULE_INFO.emergencyGoal}>
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
          info={RULE_INFO.emergencyFund}
          value={emergencyFund}
          onChange={setEmergencyFund}
        />
        <FundPicker
          label="Stagger through"
          info={RULE_INFO.staggerFund}
          value={staggerFund}
          onChange={setStaggerFund}
        />
        <Field label="Stagger from (₹)" info={RULE_INFO.staggerFrom}>
          {(id) => (
            <Input
              id={id}
              inputMode="decimal"
              placeholder="Never"
              value={draft.stagger_threshold}
              onChange={(event) => setDraft({ ...draft, stagger_threshold: event.target.value })}
            />
          )}
        </Field>
        <Field label="Stagger over (months)" info={RULE_INFO.staggerMonths}>
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
        <Field label="Minimum per fund (₹)" info={RULE_INFO.minPerFund}>
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
      <ErrorText error={save.error} />
      <div className="flex justify-end gap-2">
        {onDone && (
          <Button type="button" variant="ghost" onClick={onDone}>
            Cancel
          </Button>
        )}
        <Button type="submit" disabled={save.isPending}>
          Save rules
        </Button>
      </div>
    </form>
  )
}
