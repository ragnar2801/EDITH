import type { ReactElement } from 'react'
import type { RouteObject } from 'react-router'

import { SECTIONS } from '@/app/navigation'
import { AppShell } from '@/components/layout/AppShell'
import { BacktestPage } from '@/pages/BacktestPage'
import { BucketsPage } from '@/pages/BucketsPage'
import { CashPage } from '@/pages/CashPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { DataStatusPage } from '@/pages/DataStatusPage'
import { HoldingPage } from '@/pages/HoldingPage'
import { HoldingsPage } from '@/pages/HoldingsPage'
import { InstrumentPage } from '@/pages/InstrumentPage'
import { InstrumentsPage } from '@/pages/InstrumentsPage'
import { ModelEditorPage } from '@/pages/ModelEditorPage'
import { NotFoundPage } from '@/pages/NotFoundPage'

const PAGES: Record<string, ReactElement> = {
  '/': <DashboardPage />,
  '/buckets': <BucketsPage />,
  '/backtest': <BacktestPage />,
  '/holdings': <HoldingsPage />,
  '/cash': <CashPage />,
  '/instruments': <InstrumentsPage />,
  '/status': <DataStatusPage />,
}

export const routes: RouteObject[] = [
  {
    element: <AppShell />,
    children: [
      ...SECTIONS.map((section) => ({
        path: section.path,
        element: PAGES[section.path],
      })),
      { path: '/instruments/:id', element: <InstrumentPage /> },
      { path: '/buckets/new', element: <ModelEditorPage /> },
      { path: '/buckets/:id/edit', element: <ModelEditorPage /> },
      { path: '/backtest/:bucketId', element: <BacktestPage /> },
      { path: '/holdings/:id', element: <HoldingPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]
