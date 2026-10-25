import { NavLink, Outlet } from 'react-router'

import { SECTIONS } from '@/app/navigation'
import { BackendStatus } from '@/components/BackendStatus'
import { ConfirmProvider } from '@/components/ConfirmProvider'
import { Toaster } from '@/components/ui/sonner'
import { cn } from '@/lib/utils'

export function AppShell() {
  return (
    <ConfirmProvider>
      <div className="flex min-h-svh flex-col md:flex-row">
        <aside className="flex flex-col gap-4 border-b p-4 md:w-60 md:shrink-0 md:border-r md:border-b-0">
          <div className="flex items-center justify-between gap-2 md:flex-col md:items-start">
            <span className="text-lg font-semibold tracking-tight">Friday</span>
            <BackendStatus />
          </div>
          <nav aria-label="Main" className="flex gap-1 overflow-x-auto md:flex-col">
            {SECTIONS.map(({ path, label, icon: Icon }) => (
              <NavLink
                key={path}
                to={path}
                end={path === '/'}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-2 rounded-md px-3 py-2 text-sm whitespace-nowrap',
                    'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                    isActive && 'bg-accent text-accent-foreground font-medium',
                  )
                }
              >
                <Icon className="size-4" aria-hidden />
                {label}
              </NavLink>
            ))}
          </nav>
        </aside>
        <main className="flex-1 p-6 md:p-10">
          <Outlet />
        </main>
        <Toaster position="bottom-right" />
      </div>
    </ConfirmProvider>
  )
}
