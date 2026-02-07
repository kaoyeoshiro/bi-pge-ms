export function ErrorAlert({ message = 'Erro ao carregar dados.' }: { message?: string }) {
  return (
    <div className="rounded-lg border border-danger/20 bg-danger/5 p-4 text-sm text-danger">
      {message}
    </div>
  )
}
