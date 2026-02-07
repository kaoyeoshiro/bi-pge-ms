import { useAdminStore } from '../../stores/useAdminStore'
import { useSidebar } from './AppShell'

export function TopBar({ title }: { title: string }) {
  const { toggle } = useSidebar()
  const isAdmin = useAdminStore((s) => s.isAuthenticated)

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center border-b border-gray-200 bg-surface px-4 sm:px-6">
      <button
        onClick={toggle}
        className="mr-3 rounded-lg p-1.5 text-gray-600 hover:bg-gray-100 md:hidden"
        aria-label="Abrir menu"
      >
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>
      <h2 className="text-lg font-semibold text-primary">{title}</h2>
      {isAdmin && (
        <span className="ml-3 rounded bg-amber-500 px-2 py-0.5 text-xs font-bold text-white">
          ADMIN
        </span>
      )}
    </header>
  )
}
