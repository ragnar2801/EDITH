import { redirect, type RouteObject } from 'react-router'

import { AppShell } from '@/components/layout/AppShell'
import { FundPage } from '@/pages/FundPage'
import { FundsPage } from '@/pages/FundsPage'
import { InvestPage } from '@/pages/InvestPage'
import { ModelEditorPage } from '@/pages/ModelEditorPage'
import { ModelPage } from '@/pages/ModelPage'
import { ModelsPage } from '@/pages/ModelsPage'
import { NotFoundPage } from '@/pages/NotFoundPage'
import { PortfolioPage } from '@/pages/PortfolioPage'
import { SettingsPage } from '@/pages/SettingsPage'

/** Addresses from before the T1-22 navigation still work (D-063). */
const MOVED: [string, (params: Record<string, string | undefined>) => string][] = [
  ['/holdings', () => '/'],
  ['/holdings/:id', ({ id }) => `/funds/${id}/transactions`],
  ['/instruments', () => '/funds'],
  ['/instruments/:id', ({ id }) => `/funds/${id}`],
  ['/buckets', () => '/models'],
  ['/buckets/new', () => '/models/new'],
  ['/buckets/:id/edit', ({ id }) => `/models/${id}/edit`],
  ['/backtest', () => '/models'],
  ['/backtest/:id', ({ id }) => `/models/${id}/backtest`],
  ['/status', () => '/settings/data'],
]

export const routes: RouteObject[] = [
  {
    element: <AppShell />,
    children: [
      { path: '/', element: <PortfolioPage /> },
      { path: '/cash', element: <PortfolioPage /> },
      { path: '/invest', element: <InvestPage /> },
      { path: '/models', element: <ModelsPage /> },
      { path: '/models/new', element: <ModelEditorPage /> },
      { path: '/models/:id', element: <ModelPage /> },
      { path: '/models/:id/backtest', element: <ModelPage /> },
      { path: '/models/:id/edit', element: <ModelEditorPage /> },
      { path: '/funds', element: <FundsPage /> },
      { path: '/funds/:id', element: <FundPage /> },
      { path: '/funds/:id/transactions', element: <FundPage /> },
      { path: '/funds/:id/details', element: <FundPage /> },
      { path: '/settings', element: <SettingsPage /> },
      { path: '/settings/data', element: <SettingsPage /> },
      ...MOVED.map(
        ([path, to]) =>
          ({ path, loader: ({ params }) => redirect(to(params)) }) satisfies RouteObject,
      ),
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]
