import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'
import { Sidebar } from './Sidebar'

interface SidebarContextType {
  isOpen: boolean
  toggle: () => void
  close: () => void
}

const SidebarContext = createContext<SidebarContextType>({
  isOpen: false,
  toggle: () => {},
  close: () => {},
})

export const useSidebar = () => useContext(SidebarContext)

export function AppShell({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false)
  const toggle = () => setIsOpen((prev) => !prev)
  const close = () => setIsOpen(false)

  return (
    <SidebarContext.Provider value={{ isOpen, toggle, close }}>
      <div className="flex min-h-screen">
        <Sidebar />
        {/* Backdrop mobile */}
        {isOpen && (
          <div
            className="fixed inset-0 z-20 bg-black/50 md:hidden"
            onClick={close}
          />
        )}
        <main className="min-w-0 flex-1 overflow-x-clip md:ml-60">{children}</main>
      </div>
    </SidebarContext.Provider>
  )
}
