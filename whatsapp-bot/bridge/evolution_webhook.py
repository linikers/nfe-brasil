"""
WhatsApp Webhook Handler - Evolution API.

Persona: atendente humano, linguagem natural.
Envia: resumo em texto, PDF (DANFE), links de consulta.
"""

import json
import logging
import os
import re
import tempfile
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("nfe.whatsapp")

app = FastAPI(title="NFe WhatsApp Bot")

# Configuração
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://evolution-api:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp-server:8000/mcp")
WHATSAPP_RESTRICTED_MODE = os.getenv("WHATSAPP_RESTRICTED_MODE", "true").lower() == "true"

NFE_BUSINESS_HOUR_START = int(os.getenv("NFE_BUSINESS_HOUR_START", "8"))
NFE_BUSINESS_HOUR_END = int(os.getenv("NFE_BUSINESS_HOUR_END", "18"))
NFE_BUSINESS_DAYS = os.getenv("NFE_BUSINESS_DAYS", "0,1,2,3,4")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def detectar_intencao_nfe(texto: str) -> bool:
    texto_lower = texto.lower().strip()
    padroes = [
        r"\b\d{44}\b", r"\bnf[-\s]?e\b", r"\bnfc[-\s]?e\b", r"\bnf[-\s]?se\b",
        r"\bct[-\s]?e\b", r"\bmdf[-\s]?e\b", r"\bnota\s+fiscal", r"\bdanfe\b",
        r"\bxml\b.*\bnf", r"\bnf\b.*\bxml\b", r"\bchave\s+de\s+acesso\b",
        r"\bsefaz\b", r"\bsimples\s+nacional\b", r"\bmei\b", r"\bsped\b",
        r"\besocial\b", r"\bcnpj\b.*\bconsult", r"\bcertid[ãa]o\b",
        r"\bgerar\b.*\bnota\b", r"\benviar\b.*\bnota\b", r"\bpdf\b",
        r"\bdanfe\b", r"\bcupom\b",
    ]
    for padrao in padroes:
        if re.search(padrao, texto_lower):
            return True
    if texto.strip() in [str(i) for i in range(1, 9)]:
        return True
    return False


def dentro_do_horario() -> bool:
    from datetime import datetime
    now = datetime.now()
    dia_semana = now.weekday()
    if dia_semana not in [int(d) for d in NFE_BUSINESS_DAYS.split(",")]:
        return False
    return NFE_BUSINESS_HOUR_START <= now.hour < NFE_BUSINESS_HOUR_END


def formatar_chave(texto: str) -> str | None:
    digitos = re.sub(r"\D", "", texto)
    if len(digitos) == 44:
        return digitos
    return None


def _formatar_cnpj(cnpj: str) -> str:
    cnpj = re.sub(r"\D", "", cnpj)
    if len(cnpj) == 14:
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
    return cnpj


def _formatar_valor(valor: str | float | None) -> str:
    if not valor:
        return "R$ 0,00"
    try:
        v = float(str(valor).replace(",", "."))
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return f"R$ {valor}"


def _extrair_uf_chave(chave: str) -> str:
    """Extrai UF da chave de acesso (2 primeiros dígitos)."""
    codigos = {
        "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA",
        "16": "AP", "17": "TO", "21": "MA", "22": "PI", "23": "CE",
        "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE",
        "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
        "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT",
        "52": "GO", "53": "DF",
    }
    return codigos.get(chave[:2], "")


def _url_consulta_nfe(chave: str) -> str:
    """Gera link pra consultar a nota no portal da SEFAZ."""
    uf = _extrair_uf_chave(chave)
    # Portais de consulta por estado
    portais = {
        "AM": "https://sistemas.am.gov.br/nfe/consultanfe/",
        "BA": "https://www.sefaz.ba.gov.br/NFe/consultaNFe.asp",
        "CE": "https://www.nfe.sefaz.ce.gov.br/nfe/consultaNFe",
        "GO": "https://www.nfe.sefaz.go.gov.br/nnweb/nfrl.aspx",
        "MG": "https://www.nfe.mg.gov.br/nfe/consulta",
        "MS": "https://www.sefaz.ms.gov.br/nfe/consulta",
        "MT": "https://www.sefaz.mt.gov.br/nfse/consultanfce",
        "PE": "https://www.nfe.sefaz.pe.gov.br/nfe/consultaNFe",
        "PR": "https://www.nfe.sefaz.pr.gov.br/nfe/consultanfe",
        "RS": "https://www.sefazrs.rs.gov.br/NFCE/NFCE-COM.aspx",
        "SP": "https://www.nfe.fazenda.sp.gov.br/consultaNFe/consultaNFe.aspx",
    }
    portal = portais.get(uf, "https://www.nfe.fazenda.gov.br/portal/consultanfe.aspx")
    return f"{portal}?chave={chave}"


def _url_consulta_chave(chave: str) -> str:
    """Link genérico de consulta pela chave."""
    return f"https://www.nfe.fazenda.gov.br/portal/consultanfe.aspx?chaveAcesso={chave}"


# ---------------------------------------------------------------------------
# Envio de mensagens e arquivos
# ---------------------------------------------------------------------------

async def enviar_whatsapp(numero: str, mensagem: str, instance: str = "nfe-brasil") -> bool:
    if not EVOLUTION_API_KEY:
        return False
    url = f"{EVOLUTION_API_URL}/message/sendText/{instance}"
    headers = {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json={"number": numero, "text": mensagem}, headers=headers, timeout=30)
        return resp.status_code in (200, 201)


async def enviar_pdf_whatsapp(numero: str, caminho_pdf: str, nome_arquivo: str, instance: str = "nfe-brasil") -> bool:
    """Envia PDF como documento via Evolution API."""
    if not EVOLUTION_API_KEY or not os.path.exists(caminho_pdf):
        return False
    url = f"{EVOLUTION_API_URL}/message/sendFile/{instance}"
    headers = {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}
    # Evolution API aceita base64 ou URL do arquivo
    import base64
    with open(caminho_pdf, "rb") as f:
        pdf_b64 = base64.b64encode(f.read()).decode()
    payload = {
        "number": numero,
        "mimetype": "application/pdf",
        "fileName": nome_arquivo,
        "file": f"data:application/pdf;base64,{pdf_b64}",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers, timeout=60)
        if resp.status_code not in (200, 201):
            logger.error("Erro ao enviar PDF: %d %s", resp.status_code, resp.text[:200])
        return resp.status_code in (200, 201)


# ---------------------------------------------------------------------------
# Chamada ao MCP Server
# ---------------------------------------------------------------------------

async def call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> dict:
    async with httpx.AsyncClient() as client:
        init_resp = await client.post(
            MCP_SERVER_URL,
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize",
                  "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                             "clientInfo": {"name": "whatsapp-bot", "version": "1.0"}}},
            headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
            timeout=30,
        )
        session_id = init_resp.headers.get("mcp-session-id")
        if not session_id:
            return {"error": True}

        tool_resp = await client.post(
            MCP_SERVER_URL,
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                  "params": {"name": tool_name, "arguments": arguments}},
            headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
                     "Mcp-Session-Id": session_id},
            timeout=120,
        )
        for line in tool_resp.text.split("\n"):
            if line.startswith("data: "):
                data = json.loads(line[6:])
                result = data.get("result", {})
                if result.get("isError"):
                    return {"error": True}
                return result.get("structuredContent", result.get("content", [{}]))
    return {"error": True}


# ---------------------------------------------------------------------------
# Processamento principal
# ---------------------------------------------------------------------------

async def processar_nfe(texto: str, numero: str, instance: str) -> None:
    """Processa mensagem e ENVIA resposta (texto, PDF ou link)."""

    if not dentro_do_horario():
        await enviar_whatsapp(numero, (
            f"Olá! No momento estou fora do horário "
            f"({NFE_BUSINESS_HOUR_START}h às {NFE_BUSINESS_HOUR_END}h). "
            f"Amanhã retorno! 😊"
        ), instance)
        return

    # ==== CHAVE DE ACESSO (44 dígitos) ====
    chave = formatar_chave(texto)
    if chave:
        resultado = await call_mcp_tool("consultar_nfe", {"chave_acesso": chave})
        if "error" not in resultado:
            emitente = resultado.get("emitente", {})
            destinatario = resultado.get("destinatario", {})
            total = resultado.get("total", {})
            nome_emit = emitente.get("xNome", "o emitente")
            nome_dest = destinatario.get("xNome", "o destinatário")
            valor = _formatar_valor(total.get("vNF"))
            link = _url_consulta_nfe(chave)

            await enviar_whatsapp(numero, (
                f"Consegui consultar a nota! 😊\n\n"
                f"Emitida por *{nome_emit}*\n"
                f"Destinada a *{nome_dest}*\n"
                f"Valor total: *{valor}*\n\n"
                f"🔗 Consulte a nota completa aqui:\n{link}\n\n"
                f"Quer que eu gere o DANFE em PDF? Envie o XML da nota."
            ), instance)
        else:
            link = _url_consulta_chave(chave)
            await enviar_whatsapp(numero, (
                f"Não consegui consultar a nota pelos nossos sistemas, "
                f"mas você pode verificar direto no site da SEFAZ:\n\n"
                f"🔗 {link}\n\n"
                f"Se precisar, envie o XML que eu gero o DANFE em PDF."
            ), instance)
        return

    # ==== XML ====
    if "<?xml" in texto.lower() or "<nfe" in texto.lower():
        # Tentar gerar DANFE
        resultado_danfe = await call_mcp_tool("gerar_danfe", {"xml_content": texto})

        if "error" not in resultado_danfe and resultado_danfe.get("pdf_base64"):
            # PDF gerado com sucesso — enviar
            import base64
            pdf_b64 = resultado_danfe["pdf_base64"]
            nome_arq = resultado_danfe.get("nome_arquivo", "DANFE.pdf")
            chave_nfe = resultado_danfe.get("chave_acesso", "documento")

            # Salvar PDF temporário
            caminho = f"/tmp/{nome_arq}"
            with open(caminho, "wb") as f:
                f.write(base64.b64decode(pdf_b64))

            # Enviar PDF
            enviou = await enviar_pdf_whatsapp(numero, caminho, nome_arq, instance)

            if enviou:
                await enviar_whatsapp(numero, (
                    f"Aí está o DANFE em PDF! 📄\n"
                    f"Chave: {chave_nfe[:8]}...{chave_nfe[-4:]}\n\n"
                    f"Salve o arquivo para sua contabilidade."
                ), instance)
            else:
                # Fallback: enviar link
                resultado_parse = await call_mcp_tool("parse_nfe_xml", {"xml_content": texto})
                if "error" not in resultado_parse:
                    chave_extraida = resultado_parse.get("chave_acesso", "")
                    if chave_extraida:
                        link = _url_consulta_nfe(chave_extraida)
                        await enviar_whatsapp(numero, (
                            f"Processado o XML! 😊\n\n"
                            f"Não consegui enviar o PDF, mas aqui está o link pra consulta:\n"
                            f"🔗 {link}"
                        ), instance)
                    else:
                        await enviar_whatsapp(numero, "XML processado! Mas não extraí a chave de acesso.", instance)
                else:
                    await enviar_whatsapp(numero, "XML processado! Dados extraídos com sucesso.", instance)

            # Limpar arquivo temporário
            try:
                os.unlink(caminho)
            except OSError:
                pass
        else:
            # Não conseguiu gerar DANFE — enviar dados + link
            resultado_parse = await call_mcp_tool("parse_nfe_xml", {"xml_content": texto})
            if "error" not in resultado_parse:
                emitente = resultado_parse.get("emitente", {})
                destinatario = resultado_parse.get("destinatario", {})
                total = resultado_parse.get("total", {})
                chave_extraida = resultado_parse.get("chave_acesso", "")
                valor = _formatar_valor(total.get("vNF"))
                link = _url_consulta_nfe(chave_extraida) if chave_extraida else ""

                msg = (
                    f"XML processado! 😊\n\n"
                    f"Emitente: *{emitente.get('xNome', 'N/A')}*\n"
                    f"Destinatário: *{destinatario.get('xNome', 'N/A')}*\n"
                    f"Valor: *{valor}*\n"
                )
                if link:
                    msg += f"\n🔗 Consulte a nota: {link}\n"
                msg += "\nO DANFE em PDF pôde ser gerado. Use o link acima pra baixar direto da SEFAZ."
                await enviar_whatsapp(numero, msg, instance)
            else:
                await enviar_whatsapp(numero, (
                    "Recebi o XML mas não consegui processar. "
                    "Pode verificar se é um XML de NF-e válido?"
                ), instance)
        return

    # ==== CNPJ ====
    cnpj_match = re.search(r"\b\d{14}\b", re.sub(r"\D", "", texto))
    if cnpj_match:
        resultado = await call_mcp_tool("consultar_cnpj", {"cnpj": cnpj_match.group()})
        if "error" not in resultado:
            nome = resultado.get("razao_social", "empresa")
            situacao = resultado.get("situacao_cadastral", "desconhecida")
            cnpj_fmt = _formatar_cnpj(cnpj_match.group())
            sit_natural = {
                "ATIVA": "está ativa e regular",
                "INAPTA": "está inapta",
                "SUSPENSA": "está suspensa",
                "CANCELADA": "foi cancelada",
                "BAIXADA": "foi baixada",
            }.get(situacao.upper(), f"tem situação: {situacao}")
            await enviar_whatsapp(numero, (
                f"Encontrei a empresa! 🏢\n\n"
                f"*{nome}*\n"
                f"CNPJ: {cnpj_fmt}\n"
                f"A empresa {sit_natural}.\n\n"
                f"Quer mais alguma informação?"
            ), instance)
            return

    # ==== SEFAZ ====
    if "sefaz" in texto.lower() or "status" in texto.lower():
        uf_match = re.search(r"\b([A-Z]{2})\b", texto.upper())
        if uf_match:
            uf = uf_match.group(1)
            resultado = await call_mcp_tool("consultar_status_sefaz", {"uf": uf})
            if "error" not in resultado:
                status = resultado.get("status", "indisponível")
                if "indispon" in str(status).lower():
                    await enviar_whatsapp(numero,
                        f"A SEFAZ de {uf} está instável no momento. Tente novamente em alguns minutos.", instance)
                else:
                    await enviar_whatsapp(numero,
                        f"SEFAZ de {uf} funcionando normalmente! ✅", instance)
                return

    # ==== MENU ====
    await enviar_whatsapp(numero, (
        "Olá! 👋 Sou o assistente de notas fiscais.\n\n"
        "Posso ajudar com:\n"
        "• Consultar NF-e (envie a chave de 44 dígitos)\n"
        "• Gerar DANFE em PDF (envie o XML)\n"
        "• Consultar CNPJ de empresa\n"
        "• Verificar status da SEFAZ\n\n"
        "O que você precisa?"
    ), instance)


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------

@app.post("/webhook/evolution")
async def webhook_evolution(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"status": "error"}, status_code=400)

    event = body.get("event", "")
    if event not in ("messages.upsert", "messages.set"):
        return JSONResponse({"status": "ok"})

    data = body.get("data", {})
    instance = body.get("instance", "nfe-brasil")

    if data.get("key", {}).get("fromMe", False):
        return JSONResponse({"status": "ok"})
    if data.get("key", {}).get("remoteJid", "").endswith("@g.us"):
        return JSONResponse({"status": "ok"})

    texto = data.get("message", {}).get("conversation", "")
    if not texto:
        texto = data.get("message", {}).get("extendedTextMessage", {}).get("text", "")
    if not texto:
        return JSONResponse({"status": "ok"})

    numero = data.get("key", {}).get("remoteJid", "").replace("@s.whatsapp.net", "")
    logger.info("Mensagem de %s: %s", numero, texto[:50])

    if detectar_intencao_nfe(texto):
        await processar_nfe(texto, numero, instance)
    elif WHATSAPP_RESTRICTED_MODE:
        await enviar_whatsapp(numero,
            "Olá! No momento só posso ajudar com questões de nota fiscal. "
            "Envie uma chave, XML ou pergunte sobre NF-e. 😊", instance)

    return JSONResponse({"status": "ok"})


@app.get("/health")
async def health():
    return {"status": "ok", "service": "nfe-whatsapp-bot"}
