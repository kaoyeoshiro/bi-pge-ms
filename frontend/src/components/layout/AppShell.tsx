import type { ReactNode } from 'react'
import { Sidebar } from './Sidebar'

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="ml-60 flex-1">{children}</main>
    </div>
  )
}
