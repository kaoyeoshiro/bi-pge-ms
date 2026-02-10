import { Routes, Route } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { OverviewPage } from './pages/OverviewPage'
import { ProducaoPage } from './pages/ProducaoPage'
import { PendenciasPage } from './pages/PendenciasPage'
import { ProcessosPage } from './pages/ProcessosPage'
import { AssuntosPage } from './pages/AssuntosPage'
import { ComparativosPage } from './pages/ComparativosPage'
import { ExplorerPage } from './pages/ExplorerPage'
import { PerfilProcuradorPage } from './pages/PerfilProcuradorPage'
import { PerfilChefiaPage } from './pages/PerfilChefiaPage'
import { PerfilAssessorPage } from './pages/PerfilAssessorPage'
import { AssuntosPage } from './pages/AssuntosPage'
import { AdminPage } from './pages/AdminPage'

function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/producao" element={<ProducaoPage />} />
        <Route path="/pendencias" element={<PendenciasPage />} />
        <Route path="/processos" element={<ProcessosPage />} />
        <Route path="/assuntos" element={<AssuntosPage />} />
        <Route path="/perfil-procurador" element={<PerfilProcuradorPage />} />
        <Route path="/perfil-chefia" element={<PerfilChefiaPage />} />
        <Route path="/perfil-assessor" element={<PerfilAssessorPage />} />
        <Route path="/comparativos" element={<ComparativosPage />} />
        <Route path="/explorer" element={<ExplorerPage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Routes>
    </AppShell>
  )
}

export default App
