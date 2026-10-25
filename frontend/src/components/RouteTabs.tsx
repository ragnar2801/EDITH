import type { ReactNode } from 'react'
import { useLocation, useNavigate } from 'react-router'

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export type RouteTab = { path: string; label: string; content: ReactNode }

/** Tabs whose selection lives in the URL, so each tab can be linked to and reloaded. */
export function RouteTabs({ label, tabs }: { label: string; tabs: RouteTab[] }) {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const current = tabs.find((tab) => tab.path === pathname) ?? tabs[0]

  return (
    <Tabs value={current.path} onValueChange={(path) => navigate(path)}>
      <TabsList aria-label={label}>
        {tabs.map((tab) => (
          <TabsTrigger key={tab.path} value={tab.path}>
            {tab.label}
          </TabsTrigger>
        ))}
      </TabsList>
      {tabs.map((tab) => (
        <TabsContent key={tab.path} value={tab.path} className="flex flex-col gap-8">
          {tab.path === current.path && tab.content}
        </TabsContent>
      ))}
    </Tabs>
  )
}
