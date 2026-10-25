import { Banknote, BriefcaseBusiness, PieChart, Search, type LucideIcon } from 'lucide-react'

export type Section = {
  path: string
  label: string
  icon: LucideIcon
  /** Other paths that belong to this section, e.g. the Cash tab of Portfolio. */
  also?: string[]
}

/** The four jobs (D-063). Phase 1 is mutual funds only (D-043). */
export const SECTIONS: Section[] = [
  { path: '/', label: 'Portfolio', icon: BriefcaseBusiness, also: ['/cash'] },
  { path: '/invest', label: 'Invest', icon: Banknote },
  { path: '/models', label: 'Models', icon: PieChart },
  { path: '/funds', label: 'Funds', icon: Search },
]
