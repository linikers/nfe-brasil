# Prazos Legais NF-e

## Prazos Importantes

### Manifestação do Destinatário

| Evento | Prazo | Descrição |
|--------|-------|-----------|
| Ciência da Operação (210200) | 15 dias úteis | Obrigatório antes de confirmar/desconhecer |
| Confirmação da Operação (210210) | Sem limite | Pode ser feita a qualquer momento |
| Desconhecimento da Operação (210220) | Sem limite | Pode ser feito a qualquer momento |
| Operação não Realizada (210240) | Sem limite | Requer justificativa (mín. 15 caracteres) |

**Importante:** A Ciência (210200) é pré-requisito para obter o XML completo (procNFe). Sem ela, apenas o resumo (resNFe) fica disponível.

### Emissão de NF-e

| Prazo | Descrição |
|-------|-----------|
| Antes da saída | NF-e deve ser emitida antes da saída da mercadoria |
| Contingência | Autorização em até 24 horas após emissão |
| EPEC (desativado) | Não mais válido desde 01/07/2022 |

### Cancelamento de NF-e

| Prazo | Descrição |
|-------|-----------|
| Até 24h | Cancelamento normal (requer autorização da SEFAZ) |
| Após 24h | Carta de Correção Eletrônica (CC-e) |

### Carta de Correção Eletrônica (CC-e)

| Prazo | Descrição |
|-------|-----------|
| Sem limite | Pode ser emitida a qualquer momento |
| Limitações | Não altera: emitente, destinatário, valores, CFOP |

### Inutilização de Numeração

| Prazo | Descrição |
|-------|-----------|
| Antes da emissão | Numeração deve ser inutilizada antes do prazo |
| Até o dia 15 do mês seguinte | Inutilização de numeração não utilizada |

### Escrituração Fiscal

| Prazo | Descrição |
|-------|-----------|
| Mensal | EFD-ICMS/IPI até o dia 15 do mês seguinte |
| Mensal | EFD-Contribuições até o dia 15 do mês seguinte |
| Anual | ECD até o último dia útil de julho |
| Anual | ECF até o último dia útil de julho |

### Simples Nacional

| Prazo | Descrição |
|-------|-----------|
| Mensal | DAS até o dia 20 do mês seguinte |
| Anual | DEFIS até o dia 31 de março |

### MEI

| Prazo | Descrição |
|-------|-----------|
| Mensal | DAS até o dia 20 do mês seguinte |
| Anual | Declaração de Faturamento até o dia 31 de março |

## Cálculo de Prazos

### Dias Úteis vs Corridos
- **Dias úteis**: Segunda a sexta (exclui feriados)
- **Dias corridos**: Inclui fins de semana e feriados

### Fórmula de Prazo
```
Data Final = Data Inicial + Prazo (dias)
Se cair em dia não útil → próximo dia útil
```

### Exemplo: Ciência da Operação
```
Data de emissão: 15/06/2026
Prazo: 15 dias úteis
Data limite: 06/07/2026 (considerando feriados)
```

## Multas e Penalidades

| Infração | Multa | Descrição |
|----------|-------|-----------|
| Não emitir NF-e | R$ 500,00 por nota | Obrigação de emitir |
| Emissão fora do prazo | R$ 500,00 por nota | Atraso na emissão |
| Não manifestar destinatário | R$ 500,00 por nota | Prazo de 15 dias |
| Cancelamento indevido | R$ 500,00 por nota | Cancelamento após prazo |
| Uso de contingência indevida | R$ 500,00 por nota | tpEmis incorreto |

## Referências
- Lei Complementar 87/1996 (Lei Kandir)
- Convênio SINIEF 07/2001
- Ato COTEPE/ICMS 14/2010
- Portal Nacional da NF-e: https://www.nfe.fazenda.gov.br/portal/
