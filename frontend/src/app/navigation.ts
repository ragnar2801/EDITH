import {
  Activity,
  ArrowLeftRight,
  Banknote,
  BriefcaseBusiness,
  FlaskConical,
  LayoutDashboard,
  PieChart,
  Search,
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

/** Phase 1 is mutual funds only (D-043). */
export const SECTIONS: Section[] = [
  {
    path: '/',
    label: 'Dashboard',
    icon: LayoutDashboard,
    task: 'T1-17',
    description: 'What your funds are worth, how they have done, and how far each is from target.',
  },
  {
    path: '/buckets',
    label: 'Buckets',
    icon: PieChart,
    task: 'T1-13',
    description: 'Target splits: funds with weights, a rebalance policy and a benchmark.',
  },
  {
    path: '/backtest',
    label: 'Backtest',
    icon: FlaskConical,
    task: 'T1-14',
    description: 'How a bucket would have done: lump sum, SIP, SWP or your own timeline.',
  },
  {
    path: '/holdings',
    label: 'Holdings',
    icon: BriefcaseBusiness,
    task: 'T1-15',
    description: 'The funds you own: units and cost per fund and folio.',
  },
  {
    path: '/transactions',
    label: 'Transactions',
    icon: ArrowLeftRight,
    task: 'T1-15',
    description: 'Purchases, SIP instalments, redemptions, switches and IDCW.',
  },
  {
    path: '/cash',
    label: 'Cash',
    icon: Banknote,
    task: 'T1-16',
    description: 'INR cash with an emergency earmark, and where new cash should go.',
  },
  {
    path: '/instruments',
    label: 'Instruments',
    icon: Search,
    task: 'T1-02',
    description: 'Find any Indian mutual fund, or any NSE or US listing.',
  },
  {
    path: '/status',
    label: 'Data status',
    icon: Activity,
    task: 'T1-12',
    description: 'Fund NAVs Friday keeps and when they were last synced.',
  },
]
