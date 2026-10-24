import type { RouteObject } from 'react-router'

import { SECTIONS } from '@/app/navigation'
import { AppShell } from '@/components/layout/AppShell'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { SectionPage } from '@/pages/SectionPage'

export const routes: RouteObject[] = [
  {
    element: <AppShell />,
    children: [
      ...SECTIONS.map((section) => ({
        path: section.path,
        element: <SectionPage section={section} />,
      })),
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]
