import type { ReactNode } from 'react'

interface CardProps {
  title?: string
  children: ReactNode
  className?: string
}

export function Card({ title, children, className = '' }: CardProps) {
  return (
    <div className={`rounded-xl bg-surface shadow-sm border border-gray-100 ${className}`}>
      {title && (
        <div className="border-b border-gray-100 px-3 py-2 sm:px-5 sm:py-3">
          <h3 className="text-sm font-semibold text-gray-700">{title}</h3>
        </div>
      )}
      <div className="p-3 sm:p-5">{children}</div>
    </div>
  )
}
