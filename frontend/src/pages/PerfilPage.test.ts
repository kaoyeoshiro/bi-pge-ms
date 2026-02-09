import { describe, it, expect } from 'vitest'
import { findSelectedAssunto } from './PerfilPage'
import type { AssuntoNode } from '../types'

/**
 * Árvore simulada com 3 níveis:
 *
 * Saúde (100)
 *   ├─ Medicamentos (110)
 *   │    ├─ CBAF (111)
 *   │    └─ CEAF (112)
 *   └─ Tratamentos (120)
 * Tributário (200)
 *   └─ ICMS (210)
 */
const TREE: AssuntoNode[] = [
  {
    codigo: 100,
    nome: 'Saúde',
    nivel: 1,
    filhos: [
      {
        codigo: 110,
        nome: 'Medicamentos',
        nivel: 2,
        filhos: [
          { codigo: 111, nome: 'CBAF', nivel: 3, filhos: [] },
          { codigo: 112, nome: 'CEAF', nivel: 3, filhos: [] },
        ],
      },
      { codigo: 120, nome: 'Tratamentos', nivel: 2, filhos: [] },
    ],
  },
  {
    codigo: 200,
    nome: 'Tributário',
    nivel: 1,
    filhos: [
      { codigo: 210, nome: 'ICMS', nivel: 2, filhos: [] },
    ],
  },
]

describe('findSelectedAssunto', () => {
  it('retorna null para lista vazia de códigos', () => {
    expect(findSelectedAssunto(TREE, [])).toBeNull()
  })

  it('encontra assunto raiz selecionado com path de 1 nível', () => {
    // Simula seleção de "Saúde" — selectedCodes contém Saúde + todos descendentes
    const selectedCodes = [100, 110, 111, 112, 120]
    const result = findSelectedAssunto(TREE, selectedCodes)

    expect(result).not.toBeNull()
    expect(result!.codigo).toBe(100)
    expect(result!.nome).toBe('Saúde')
    expect(result!.path).toEqual([
      { codigo: 100, nome: 'Saúde' },
    ])
  })

  it('encontra assunto filho com path de 2 níveis (Saúde → Medicamentos)', () => {
    // Simula seleção de "Medicamentos" — selectedCodes contém Medicamentos + descendentes
    const selectedCodes = [110, 111, 112]
    const result = findSelectedAssunto(TREE, selectedCodes)

    expect(result).not.toBeNull()
    expect(result!.codigo).toBe(110)
    expect(result!.nome).toBe('Medicamentos')
    expect(result!.path).toEqual([
      { codigo: 100, nome: 'Saúde' },
      { codigo: 110, nome: 'Medicamentos' },
    ])
  })

  it('encontra assunto neto com path de 3 níveis (Saúde → Medicamentos → CBAF)', () => {
    // Simula seleção de "CBAF" — nó folha, selectedCodes contém apenas CBAF
    const selectedCodes = [111]
    const result = findSelectedAssunto(TREE, selectedCodes)

    expect(result).not.toBeNull()
    expect(result!.codigo).toBe(111)
    expect(result!.nome).toBe('CBAF')
    expect(result!.path).toEqual([
      { codigo: 100, nome: 'Saúde' },
      { codigo: 110, nome: 'Medicamentos' },
      { codigo: 111, nome: 'CBAF' },
    ])
  })

  it('prioriza nó mais raso quando há múltiplos matches em diferentes ramos', () => {
    // Se selectedCodes contém Saúde (raiz) e ICMS (nível 2), retorna Saúde (mais raso)
    const selectedCodes = [100, 210]
    const result = findSelectedAssunto(TREE, selectedCodes)

    expect(result).not.toBeNull()
    expect(result!.codigo).toBe(100)
    expect(result!.nome).toBe('Saúde')
  })

  it('retorna null quando código não existe na árvore', () => {
    const selectedCodes = [999]
    const result = findSelectedAssunto(TREE, selectedCodes)

    expect(result).toBeNull()
  })
})
