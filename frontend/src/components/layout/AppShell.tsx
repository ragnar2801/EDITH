import { Plus, Settings } from 'lucide-react'
import { NavLink, Outlet, useLocation } from 'react-router'

import { SECTIONS, type Section } from '@/app/navigation'
import { ConfirmProvider } from '@/components/ConfirmProvider'
import { AddTransactionProvider } from '@/components/holdings/AddTransactionProvider'
import { Button } from '@/components/ui/button'
import { Toaster } from '@/components/ui/sonner'
import { useAddTransaction } from '@/hooks/use-add-transaction'
import { cn } from '@/lib/utils'

import { NavFreshness } from './NavFreshness'

function isActive(section: Section, pathname: string): boolean {
  if (section.path === '/') return pathname === '/' || (section.also ?? []).includes(pathname)
  return pathname === section.path || pathname.startsWith(`${section.path}/`)
}

export function AppShell() {
  return (
    <ConfirmProvider>
      <AddTransactionProvider>
        <Layout />
        <Toaster position="bottom-right" />
      </AddTransactionProvider>
    </ConfirmProvider>
  )
}

function Layout() {
  const { pathname } = useLocation()
  const addTransaction = useAddTransaction()

  return (
    <div className="flex min-h-svh flex-col">
      <header className="bg-background/95 supports-[backdrop-filter]:bg-background/80 sticky top-0 z-40 border-b backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-4 md:px-6">
          <NavLink to="/" className="text-lg font-semibold tracking-tight">
            Friday
          </NavLink>
          <nav aria-label="Main" className="hidden items-center gap-1 md:flex">
            {SECTIONS.map((section) => (
              <NavLink
                key={section.path}
                to={section.path}
                className={cn(
                  'rounded-md px-3 py-1.5 text-sm',
                  'text-muted-foreground hover:text-foreground',
                  isActive(section, pathname) && 'bg-accent text-foreground font-medium',
                )}
              >
                {section.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-1">
            <NavFreshness />
            <Button size="sm" className="hidden md:inline-flex" onClick={() => addTransaction()}>
              <Plus /> Add
            </Button>
            <Button asChild variant="ghost" size="icon" aria-label="Settings">
              <NavLink to="/settings">
                <Settings />
              </NavLink>
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 pt-6 pb-24 md:px-6 md:pt-8 md:pb-10">
        <Outlet />
      </main>

      {/* Phones: the same four jobs as a bottom tab bar, and a floating Add. */}
      <Button
        size="icon"
        className="fixed right-4 bottom-20 z-40 size-12 rounded-full shadow-lg md:hidden"
        aria-label="Add transaction"
        onClick={() => addTransaction()}
      >
        <Plus className="size-5" />
      </Button>
      <nav
        aria-label="Sections"
        className="bg-background fixed inset-x-0 bottom-0 z-40 grid grid-cols-4 border-t md:hidden"
      >
        {SECTIONS.map((section) => (
          <NavLink
            key={section.path}
            to={section.path}
            className={cn(
              'text-muted-foreground flex flex-col items-center gap-0.5 py-2 text-xs',
              isActive(section, pathname) && 'text-foreground font-medium',
            )}
          >
            <section.icon className="size-5" aria-hidden />
            {section.label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
