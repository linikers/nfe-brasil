# NFe Brasil

<p align="center">
  <strong>MCP Server + WhatsApp Bot para Notas Fiscais Brasileiras</strong>
</p>

<p align="center">
  <a href="https://github.com/linikers/nfe-brasil"><img src="https://img.shields.io/github/license/linikers/nfe-brasil?color=009c3b" alt="License MIT"></a>
  <a href="https://pypi.org/project/nfe-brasil/"><img src="https://img.shields.io/pypi/v/nfe-brasil?color=009c3b&label=PyPI" alt="PyPI version"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%2B-002776?logo=python&logoColor=white" alt="Python 3.10+"></a>
  <img src="https://img.shields.io/badge/MCP-compatível-7c3aed" alt="MCP Compatible">
</p>

---

## O que é

**NFe Brasil** é um servidor MCP + WhatsApp Bot completo para notas fiscais brasileiras. Consulte NF-e, NFS-e, CT-e, MDF-e, NFC-e, SPED, eSocial e Reforma Tributária via linguagem natural.

**Baseado em:** [mcp-fiscal-brasil](https://github.com/DeHor-Labs/mcp-fiscal-brasil) (DeHor-Labs, MIT License)

### Por que NFe Brasil?

| Feature | NFe Brasil | mcp-fiscal-brasil |
|---------|:----------:|:------------------:|
| NF-e (parse, validação, DANFE) | ✅ | ✅ |
| NFS-e (consulta municipal) | ✅ | ✅ |
| CT-e (Conhecimento de Transporte) | ✅ | ❌ |
| MDF-e (Manifesto de Documentos) | ✅ | ❌ |
| NFC-e (Cupom Fiscal) | ✅ | ❌ |
| SPED (EFD-ICMS, EFD-Contribuições) | ✅ | ✅ |
| eSocial | ✅ | ✅ |
| Reforma Tributária 2026 (IBS/CBS) | ✅ | ✅ |
| WhatsApp Bot integrado | ✅ | ❌ |
| Modo Restrito (só NF-e) | ✅ | ❌ |
| Backup XML via email | ✅ | ❌ |
| Organização automática de XMLs | ✅ | ❌ |
| Códigos de retorno SEFAZ | ✅ | ❌ |
| Tabela de contingência | ✅ | ❌ |
| Docker deploy | ✅ | ✅ |

---

## Início Rápido

### Opção 1: MCP Server (para IAs)

```bash
# Instalar
pip install nfe-brasil

# Rodar (HTTP mode)
nfe-brasil --transport http --port 8000

# Ou via uvx (zero instalação)
uvx nfe-brasil
```

### Opção 2: Docker (recomendado para produção)

```bash
# Clonar
git clone https://github.com/linikers/nfe-brasil.git
cd nfe-brasil

# Configurar WhatsApp (opcional)
cp whatsapp-bot/.env.example whatsapp-bot/.env
# Editar .env com seu token

# Rodar
docker-compose up -d
```

### Opção 3: Claude Desktop

Edite `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "nfe-brasil": {
      "command": "uvx",
      "args": ["nfe-brasil"]
    }
  }
}
```

---

## Ferramentas Disponíveis (44 tools)

### NF-e
- `consultar_nfe` - Consulta por chave de acesso
- `validar_chave_nfe` - Valida dígito verificador
- `parse_nfe_xml` - Parse XML completo
- `gerar_danfe` - Gera DANFE em PDF
- `validar_assinatura_nfe` - Valida XMLDSig
- `baixar_nfe_distribuicao` - Baixa via NFeDistribuicaoDFe (mTLS A1)
- `manifestar_nfe` - Manifestação do destinatário
- `consultar_status_sefaz` - Status SEFAZ por UF

### NFS-e
- `consultar_nfse` - Consulta com mapeamento municipal

### CNPJ/CPF
- `consultar_cnpj` - Dados cadastrais completos
- `validar_cpf` - Validação offline

### Simples/MEI
- `consultar_simples_nacional` - Situação no SN/MEI

### SPED
- `analisar_sped` - Análise de arquivos SPED
- `listar_registros_sped` - Lista registros específicos

### eSocial
- `listar_eventos_esocial` - Catálogo de eventos
- `validar_evento_esocial` - Validação de XML

### Tabelas
- `consultar_ncm`, `consultar_cfop`, `consultar_cnae`, etc.

### Reforma Tributária
- `simular_transicao_reforma_tributaria` - Projeção 2026-2033

### Agentic (alto nível)
- `analyze_cnpj_compliance` - Score 0-100
- `risk_score_supplier` - Due diligence
- `validate_nfe_full` - Validação consolidada
- `summarize_sped` - Resumo executivo

---

## Estrutura do Monorepo

```
nfe-brasil/
├── mcp-server/              ← MCP Server (ferramentas)
│   ├── src/nfe_brasil/      ← Código fonte Python
│   ├── tests/               ← Testes
│   └── pyproject.toml
├── whatsapp-bot/            ← WhatsApp Bot
│   ├── bridge/              ← Cloud API webhook
│   ├── bot/                 ← Handler NF-e
│   └── requirements.txt
├── shared/                  ← Conhecimento compartilhado
│   ├── docs/                ← Documentação NF-e
│   ├── scripts/             ← Scripts auxiliares
│   └── templates/           ← Templates DANFE/email
├── docker-compose.yml       ← Deploy completo
└── README.md
```

---

## WhatsApp Bot

### Configuração

1. Criar app no [Meta for Developers](https://developers.facebook.com/)
2. Ativar WhatsApp Cloud API
3. Configurar webhook: `https://seu-dominio.com/webhook`
4. Copiar `.env.example` para `.env` e preencher:

```env
WHATSAPP_TOKEN=seu_token
WHATSAPP_PHONE_ID=seu_phone_id
WHATSAPP_VERIFY_TOKEN=nfe-brasil-verify
WHATSAPP_RESTRICTED_MODE=true
```

### Modo Restrito

Quando `WHATSAPP_RESTRICTED_MODE=true`, o bot só responde sobre notas fiscais. Mensagens sobre outros assuntos recebem uma recusa educada.

### Fluxo

```
WhatsApp Cliente → Meta Graph API → cloud_api.py (porta 3001)
                                        │
                                   detectar_intencao_nfe()
                                        │
                           ┌────────────┴────────────┐
                           ▼                         ▼
                    handle_nfe_message()       Hermes Agent
                    (fiscal)                   (geral)
                           │
                    ├─ Consulta NF-e
                    ├─ Validação XML
                    ├─ Status SEFAZ
                    ├─ Geração DANFE
                    └─ Consulta CNPJ
```

---

## Documentação

- [Códigos de Retorno SEFAZ](shared/docs/codigos-retorno-sefaz.md)
- [Contingência NF-e](shared/docs/contingencia.md)
- [Prazos Legais](shared/docs/prazos-legais.md)

---

## Scripts Auxiliares

```bash
# Backup de XMLs via email
python shared/scripts/backup-xml-email.py user@gmail.com senha 7

# Organizar XMLs por data/CNPJ
python shared/scripts/organizar-xmls.py ./xmls_brutos ./xmls_organizados
```

---

## Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

---

## Licença

MIT License - Veja [LICENSE](LICENSE) para detalhes.

**Créditos:** Baseado em [mcp-fiscal-brasil](https://github.com/DeHor-Labs/mcp-fiscal-brasil) por [Nikolas de Hor](https://github.com/NikolasHor).

---

## Agradecimentos

- [DeHor-Labs](https://github.com/DeHor-Labs) - Código base do MCP Server
- [CONFAZ](http://www.confaz.fazenda.gov.br/) - Padrões fiscais
- [Portal Nacional NF-e](https://www.nfe.fazenda.gov.br/) - Documentação oficial
