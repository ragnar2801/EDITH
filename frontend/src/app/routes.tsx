import type { ReactElement } from 'react'
import type { RouteObject } from 'react-router'

import { SECTIONS } from '@/app/navigation'
import { AppShell } from '@/components/layout/AppShell'
import { InstrumentPage } from '@/pages/InstrumentPage'
import { InstrumentsPage } from '@/pages/InstrumentsPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { SectionPage } from '@/pages/SectionPage'

/** Sections whose task has built them. The rest show a placeholder. */
const BUILT: Record<string, ReactElement> = {
  '/instruments': <InstrumentsPage />,
}

export const routes: RouteObject[] = [
  {
    element: <AppShell />,
    children: [
      ...SECTIONS.map((section) => ({
        path: section.path,
        element: BUILT[section.path] ?? <SectionPage section={section} />,
      })),
      { path: '/instruments/:id', element: <InstrumentPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]
