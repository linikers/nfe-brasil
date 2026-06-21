# Contingência NF-e - Tipos de Emissão (tpEmis)

## Tabela de Modalidades de Emissão

| Código | Modalidade | Descrição | Quando Usar |
|--------|------------|-----------|-------------|
| 1 | Normal | Emissão padrão via SEFAZ autorizadora | Situação normal |
| 2 | Contingência FS | Formulário de Segurança | SEFAZ indisponível |
| 3 | Contingência SCAN | Sistema de Contingência do Ambiente Nacional | SEFAZ indisponível |
| 4 | Contingência DPEC | Declaração Prévia de Emissão em Contingência | SEFAZ indisponível |
| 5 | Contingência FS-DA | Formulário de Segurança para DANFE | SEFAZ indisponível + impressão |
| 6 | Contingência SVC-AN | SEFAZ Virtual de Contingência - Ambiente Nacional | SEFAZ RS caiu |
| 7 | Contingência SVC-RS | SEFAZ Virtual de Contingência - Rio Grande do Sul | SEFAZ AN caiu |
| 9 | Contingência EPEC | Evento Prévio de Emissão em Contingência | OFF desde 2022 |

## Detalhamento por Modalidade

### tpEmis = 1 (Normal)
- Padrão para todas as emissões
- Autorização realizada pela SEFAZ autorizadora do estado
- XML assinado e transmitido normalmente

### tpEmis = 2 (Contingência FS)
- Formulário de Segurança (FS) emitido pela autoridade fazendária
- Usado quando o contribuinte não possui acesso à internet
- DANFE impresso em formulário de segurança

### tpEmis = 3 (Contingência SCAN)
- Sistema de Contingência do Ambiente Nacional
- Utiliza webservice de contingência (SVAN ou SVC)
- Autorização em até 24 horas após a emissão

### tpEmis = 4 (Contingência DPEC)
- Declaração Prévia de Emissão em Contingência
- Envia resumo da NF-e (DPEC) para a SEFAZ
- Autorização em até 7 dias úteis

### tpEmis = 5 (Contingência FS-DA)
- Formulário de Segurança para impressão do DANFE
- Similar ao FS, mas com formulário específico para DANFE
- Usado quando não há acesso à internet

### tpEmis = 6 (Contingência SVC-AN)
- SEFAZ Virtual de Contingência - Ambiente Nacional
- Usado quando o SVRS (Sefaz Virtual do Rio Grande do Sul) estiver indisponível
- Autorização automática pelo Ambiente Nacional

### tpEmis = 7 (Contingência SVC-RS)
- SEFAZ Virtual de Contingência - Rio Grande do Sul
- Usado quando o Ambiente Nacional (SVAN) estiver indisponível
- Autorização automática pelo SVRS

### tpEmis = 9 (Contingência EPEC)
- Evento Prévio de Emissão em Contingência
- **DESATIVADO desde 01/07/2022**
- Não deve mais ser utilizado

## Fluxo de Contingência

```
SEFAZ Autorizadora Indisponível
         ↓
Verificar qual contingência usar
         ↓
┌─────────────────────────────────┐
│ tpEmis = 6 (SVC-AN)            │
│ SEFAZ do RS caiu                │
│ Usa Ambiente Nacional           │
├─────────────────────────────────┤
│ tpEmis = 7 (SVC-RS)            │
│ Ambiente Nacional caiu          │
│ Usa SEFAZ do RS                 │
├─────────────────────────────────┤
│ tpEmis = 3 (SCAN)              │
│ Qualquer SEFAZ indisponível     │
│ Usa webservice de contingência  │
└─────────────────────────────────┘
         ↓
Emissão com tpEmis correto
         ↓
Autorização em até 24h
         ↓
Se não autorizado: carta de correção
```

## Observações Importantes

1. **NFC-e (modelo 65)**: Não aceita contingência FS/FS-DA
2. **Contingência SVC**: Requer que a SEFAZ autorizadora esteja configurada
3. **Prazo de autorização**: Máximo 24 horas após emissão em contingência
4. **Carta de Correção**: Se não autorizado em contingência, emita CC-e
5. **Inutilização de números**: Em contingência, use apenas números autorizados

## Referências
- Portal Nacional da NF-e: https://www.nfe.fazenda.gov.br/portal/
- Leiaute da NF-e v4.00: https://www.portalfiscal.inf.br/nfe/
