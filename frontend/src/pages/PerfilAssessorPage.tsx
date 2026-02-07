import { PerfilPage } from './PerfilPage'
import { useAssessores } from '../api/hooks/useFilters'

export function PerfilAssessorPage() {
  const { data: assessores } = useAssessores()

  return (
    <PerfilPage
      title="Perfil do Assessor"
      dimensao="assessor"
      placeholder="Selecione o assessor"
      options={assessores}
      showProcuradorChart
    />
  )
}
