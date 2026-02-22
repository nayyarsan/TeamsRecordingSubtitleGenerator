export default function Sidebar({ children, className = '' }) {
  return (
    <aside className={`w-80 bg-surface border-l border-border overflow-y-auto flex flex-col ${className}`}>
      {children}
    </aside>
  )
}
