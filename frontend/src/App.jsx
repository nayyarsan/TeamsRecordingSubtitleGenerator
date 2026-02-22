import { Routes, Route } from 'react-router-dom'
import Header from './components/layout/Header'
import DashboardPage from './components/dashboard/DashboardPage'
import WorkspacePage from './components/workspace/WorkspacePage'

export default function App() {
  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Header />
      <main className="flex-1 overflow-hidden">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/workspace/:videoId" element={<WorkspacePage />} />
        </Routes>
      </main>
    </div>
  )
}
