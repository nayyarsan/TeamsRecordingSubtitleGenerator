import { Link, useLocation } from 'react-router-dom'

export default function Header() {
  const { pathname } = useLocation()
  const isWorkspace = pathname.startsWith('/workspace')

  return (
    <header className="h-12 bg-surface border-b border-border flex items-center px-4 shrink-0">
      <Link to="/" className="font-semibold text-sm tracking-wide text-white hover:text-primary transition-colors">
        MediaProcessor
      </Link>

      {isWorkspace && (
        <nav className="ml-6 flex gap-4 text-xs text-gray-400">
          <Link to="/" className="hover:text-white">Dashboard</Link>
        </nav>
      )}

      <div className="ml-auto flex items-center gap-3 text-xs text-gray-400">
        <span>v1.0</span>
      </div>
    </header>
  )
}
