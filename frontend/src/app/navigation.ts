import {
  Activity,
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
}

/** Phase 1 is mutual funds only (D-043). Only built screens are listed (D-060). */
export const SECTIONS: Section[] = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/holdings', label: 'Holdings', icon: BriefcaseBusiness },
  { path: '/cash', label: 'Cash', icon: Banknote },
  { path: '/buckets', label: 'Models', icon: PieChart },
  { path: '/backtest', label: 'Backtest', icon: FlaskConical },
  { path: '/instruments', label: 'Funds', icon: Search },
  { path: '/status', label: 'Data status', icon: Activity },
]
