import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { Section } from '@/app/navigation'

/** Placeholder for a Phase 1 page until its task builds it. */
export function SectionPage({ section }: { section: Section }) {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{section.label}</h1>
        <p className="text-muted-foreground mt-1">{section.description}</p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Not built yet</CardTitle>
          <CardDescription>
            Arrives in {section.task}. See <code>docs/tasks/phase-1.md</code>.
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  )
}
