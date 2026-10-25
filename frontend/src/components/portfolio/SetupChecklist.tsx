import { CheckCircle2, Circle } from 'lucide-react'
import type { ReactNode } from 'react'

import { Section } from '@/components/Section'
import { cn } from '@/lib/utils'

export type SetupStep = { label: string; done: boolean; action: ReactNode }

/** First run: three steps to a working Friday; gone once all are done (J1). */
export function SetupChecklist({ steps }: { steps: SetupStep[] }) {
  if (steps.every((step) => step.done)) return null
  return (
    <Section title="Get set up">
      <ol className="divide-y rounded-lg border">
        {steps.map((step) => (
          <li key={step.label} className="flex items-center gap-3 px-4 py-3">
            {step.done ? (
              <CheckCircle2 className="text-positive size-5 shrink-0" aria-label="Done" />
            ) : (
              <Circle className="text-muted-foreground size-5 shrink-0" aria-label="To do" />
            )}
            <span className={cn('text-sm', step.done && 'text-muted-foreground line-through')}>
              {step.label}
            </span>
            {!step.done && <span className="ml-auto">{step.action}</span>}
          </li>
        ))}
      </ol>
    </Section>
  )
}
