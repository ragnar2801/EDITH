import {
  ArrowLeftRight,
  Banknote,
  BriefcaseBusiness,
  Eye,
  LayoutDashboard,
  Send,
  Activity,
  type LucideIcon,
} from 'lucide-react'

export type Section = {
  path: string
  label: string
  icon: LucideIcon
  /** The Phase 1 task that fills this page in (docs/tasks/phase-1.md). */
  task: string
  description: string
}

export const SECTIONS: Section[] = [
  {
    path: '/',
    label: 'Dashboard',
    icon: LayoutDashboard,
    task: 'T1-08',
    description: 'Portfolio value, P&L, allocation and XIRR, in INR and USD.',
  },
  {
    path: '/holdings',
    label: 'Holdings',
    icon: BriefcaseBusiness,
    task: 'T1-03',
    description: 'What you own: units and cost per holding, with lots.',
  },
  {
    path: '/transactions',
    label: 'Transactions',
    icon: ArrowLeftRight,
    task: 'T1-03',
    description: 'Buys, sells, dividends, splits and bonuses.',
  },
  {
    path: '/cash',
    label: 'Cash',
    icon: Banknote,
    task: 'T1-04',
    description: 'Cash accounts in INR and USD, with earmarks.',
  },
  {
    path: '/remittances',
    label: 'Remittances & LRS',
    icon: Send,
    task: 'T1-04',
    description: 'Money sent to the US, with LRS and TCS totals per financial year.',
  },
  {
    path: '/watchlist',
    label: 'Watchlist',
    icon: Eye,
    task: 'T1-07',
    description: 'Stocks and funds you are watching, with your reasons and buy zones.',
  },
  {
    path: '/status',
    label: 'Data status',
    icon: Activity,
    task: 'T1-09',
    description: 'When prices were last fetched and how the daily jobs ran.',
  },
]
