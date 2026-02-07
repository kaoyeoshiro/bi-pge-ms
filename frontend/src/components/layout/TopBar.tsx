export function TopBar({ title }: { title: string }) {
  return (
    <header className="sticky top-0 z-20 flex h-14 items-center border-b border-gray-200 bg-surface px-6">
      <h2 className="text-lg font-semibold text-primary">{title}</h2>
    </header>
  )
}
