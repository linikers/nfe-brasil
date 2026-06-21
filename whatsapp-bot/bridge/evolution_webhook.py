"""
WhatsApp Webhook Handler - Evolution API.

Persona: atendente humano, linguagem natural, sem códigos técnicos.
Nunca mostrar: chaves de acesso brutas, códigos de erro, campos XML,
cabeçalhos como "Hermes" ou "Assistente". Toda resposta deve parecer
de uma pessoa real ajudando com nota fiscal.
"""

import json
import logging
import os
import re
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

# Horário comercial
NFE_BUSINESS_HOUR_START = int(os.getenv("NFE_BUSINESS_HOUR_START", "8"))
NFE_BUSINESS_HOUR_END = int(os.getenv("NFE_BUSINESS_HOUR_END", "18"))
NFE_BUSINESS_DAYS = os.getenv("NFE_BUSINESS_DAYS", "0,1,2,3,4")


# ---------------------------------------------------------------------------
# Respostas naturais (persona humana)
# ---------------------------------------------------------------------------

def detectar_intencao_nfe(texto: str) -> bool:
    """Detecta se a mensagem é sobre nota fiscal."""
    texto_lower = texto.lower().strip()

    padroes = [
        r"\b\d{44}\b",
        r"\bnf[-\s]?e\b",
        r"\bnfc[-\s]?e\b",
        r"\bnf[-\s]?se\b",
        r"\bct[-\s]?e\b",
        r"\bmdf[-\s]?e\b",
        r"\bnota\s+fiscal",
        r"\bdanfe\b",
        r"\bxml\b.*\bnf",
        r"\bnf\b.*\bxml\b",
        r"\bchave\s+de\s+acesso\b",
        r"\bsefaz\b",
        r"\bsimples\s+nacional\b",
        r"\bmei\b",
        r"\bsped\b",
        r"\besocial\b",
        r"\bcnpj\b.*\bconsult",
        r"\bcertid[ãa]o\b",
    ]

    for padrao in padroes:
        if re.search(padrao, texto_lower):
            return True

    # Menus numéricos
    if texto.strip() in [str(i) for i in range(1, 9)]:
        return True

    return False


def dentro_do_horario() -> bool:
    """Verifica se está dentro do horário comercial."""
    from datetime import datetime
    now = datetime.now()
    dia_semana = now.weekday()
    if dia_semana not in [int(d) for d in NFE_BUSINESS_DAYS.split(",")]:
        return False
    return NFE_BUSINESS_HOUR_START <= now.hour < NFE_BUSINESS_HOUR_END


def formatar_chave(texto: str) -> str | None:
    """Extrai chave de 44 dígitos."""
    digitos = re.sub(r"\D", "", texto)
    if len(digitos) == 44:
        return digitos
    return None


def _formatar_cnpj(cnpj: str) -> str:
    """Formata CNPJ: 12.345.678/0001-90"""
    cnpj = re.sub(r"\D", "", cnpj)
    if len(cnpj) == 14:
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
    return cnpj


def _formatar_valor(valor: str | float | None) -> str:
    """Formata valor: R$ 1.234,56"""
    if not valor:
        return "R$ 0,00"
    try:
        v = float(str(valor).replace(",", "."))
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return f"R$ {valor}"


# ---------------------------------------------------------------------------
# Envio de mensagens
# ---------------------------------------------------------------------------

async def enviar_whatsapp(numero: str, mensagem: str, instance: str = "nfe-brasil") -> bool:
    """Envia mensagem via Evolution API."""
    if not EVOLUTION_API_KEY:
        logger.warning("Evolution API não configurada")
        return False

    url = f"{EVOLUTION_API_URL}/message/sendText/{instance}"
    headers = {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}
    payload = {"number": numero, "text": mensagem}

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code not in (200, 201):
            logger.error("Evolution API erro %d: %s", resp.status_code, resp.text[:200])
            return False
        return True


# ---------------------------------------------------------------------------
# Chamada ao MCP Server
# ---------------------------------------------------------------------------

async def call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> dict:
    """Chama uma tool do MCP Server."""
    async with httpx.AsyncClient() as client:
        init_resp = await client.post(
            MCP_SERVER_URL,
            json={
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "whatsapp-bot", "version": "1.0"},
                },
            },
            headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
            timeout=30,
        )

        session_id = init_resp.headers.get("mcp-session-id")
        if not session_id:
            return {"error": "Serviço temporariamente indisponível. Tente novamente em instantes."}

        tool_resp = await client.post(
            MCP_SERVER_URL,
            json={
                "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            },
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Mcp-Session-Id": session_id,
            },
            timeout=60,
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
# Processamento - LINGUAGEM 100% NATURAL
# ---------------------------------------------------------------------------

async def processar_nfe(texto: str) -> str | None:
    """Processa mensagem fiscal e retorna resposta em linguagem natural."""

    # Fora do horário
    if not dentro_do_horario():
        return (
            f"Olá! No momento estou fora do horário de atendimento "
            f"(das {NFE_BUSINESS_HOUR_START}h às {NFE_BUSINESS_HOUR_END}h). "
            f"Amanhã retorno! 😊"
        )

    # Chave de acesso (44 dígitos)
    chave = formatar_chave(texto)
    if chave:
        resultado = await call_mcp_tool("consultar_nfe", {"chave_acesso": chave})
        if "error" in resultado:
            return (
                "Não consegui localizar essa nota. Pode verificar se a "
                "chave está correta? São 44 dígitos, você encontra no DANFE."
            )

        emitente = resultado.get("emitente", {})
        destinatario = resultado.get("destinatario", {})
        total = resultado.get("total", {})
        nome_emitente = emitente.get("xNome", "o emitente")
        nome_dest = destinatario.get("xNome", "o destinatário")
        valor = _formatar_valor(total.get("vNF"))

        return (
            f"Consegui consultar a nota! 😊\n\n"
            f"Emitida por *{nome_emitente}*\n"
            f"Destinada a *{nome_dest}*\n"
            f"Valor total: *{valor}*\n\n"
            f"Posso gerar o DANFE em PDF ou validar o XML se precisar. "
            f"O que mais posso ajudar?"
        )

    # XML
    if "<?xml" in texto.lower() or "<nfe" in texto.lower():
        resultado = await call_mcp_tool("parse_nfe_xml", {"xml_content": texto})
        if "error" in resultado:
            return "Não consegui processar esse XML. Pode verificar se é um XML de NF-e válido?"
        return (
            "Recebi o XML! 📄 Consegui processar ele certinho. "
            "Quer que eu gere o DANFE em PDF ou faça alguma outra verificação?"
        )

    # Consulta CNPJ
    cnpj_match = re.search(r"\b\d{14}\b", re.sub(r"\D", "", texto))
    if cnpj_match:
        resultado = await call_mcp_tool("consultar_cnpj", {"cnpj": cnpj_match.group()})
        if "error" not in resultado:
            nome = resultado.get("razao_social", "empresa")
            situacao = resultado.get("situacao_cadastral", "desconhecida")
            cnpj_fmt = _formatar_cnpj(cnpj_match.group())

            # Traduzir situação
            sit_natural = {
                "ATIVA": "está ativa e regular",
                "INAPTA": "está inapta",
                "SUSPENSA": "está suspensa",
                "CANCELADA": "foi cancelada",
                "BAIXADA": "foi baixada",
            }.get(situacao.upper(), f"tem situação cadastral: {situacao}")

            return (
                f"Encontrei a empresa! 🏢\n\n"
                f"*{nome}*\n"
                f"CNPJ: {cnpj_fmt}\n"
                f"A empresa {sit_natural}.\n\n"
                f"Quer saber mais alguma coisa sobre ela?"
            )

    # Consulta SEFAZ
    if "sefaz" in texto.lower() or "status" in texto.lower():
        uf_match = re.search(r"\b([A-Z]{2})\b", texto.upper())
        if uf_match:
            uf = uf_match.group(1)
            resultado = await call_mcp_tool("consultar_status_sefaz", {"uf": uf})
            if "error" not in resultado:
                status = resultado.get("status", "indisponível")
                if "indispon" in str(status).lower():
                    return (
                        f"O serviço da SEFAZ de {uf} está instável no momento. "
                        f"Se precisar emitir nota, tente novamente em alguns minutos."
                    )
                return f"O serviço da SEFAZ de {uf} está funcionando normalmente! ✅"

    # Menu / Saudação
    return (
        "Olá! 👋 Sou o assistente de notas fiscais.\n\n"
        "Posso ajudar com:\n"
        "• Consultar uma NF-e (envie a chave de 44 dígitos)\n"
        "• Validar XML de nota fiscal\n"
        "• Consultar CNPJ de empresa\n"
        "• Verificar status da SEFAZ\n\n"
        "O que você precisa?"
    )


# ---------------------------------------------------------------------------
# Webhook - Recebe mensagens da Evolution API
# ---------------------------------------------------------------------------

@app.post("/webhook/evolution")
async def webhook_evolution(request: Request):
    """Recebe webhook da Evolution API."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"status": "error"}, status_code=400)

    event = body.get("event", "")

    if event not in ("messages.upsert", "messages.set"):
        return JSONResponse({"status": "ok"})

    data = body.get("data", {})
    instance = body.get("instance", "nfe-brasil")

    # Ignorar mensagens enviadas por nós
    if data.get("key", {}).get("fromMe", False):
        return JSONResponse({"status": "ok"})

    # Ignorar grupos
    if data.get("key", {}).get("remoteJid", "").endswith("@g.us"):
        return JSONResponse({"status": "ok"})

    # Extrair texto
    texto = data.get("message", {}).get("conversation", "")
    if not texto:
        texto = data.get("message", {}).get("extendedTextMessage", {}).get("text", "")

    if not texto:
        return JSONResponse({"status": "ok"})

    numero = data.get("key", {}).get("remoteJid", "").replace("@s.whatsapp.net", "")

    logger.info("Mensagem de %s: %s", numero, texto[:50])

    # Detectar intenção
    if detectar_intencao_nfe(texto):
        resposta = await processar_nfe(texto)
        if resposta:
            await enviar_whatsapp(numero, resposta, instance)
    elif WHATSAPP_RESTRICTED_MODE:
        await enviar_whatsapp(
            numero,
            "Olá! No momento só posso ajudar com questões de nota fiscal. "
            "Envie uma chave de acesso, XML ou pergunte sobre NF-e. 😊",
            instance,
        )

    return JSONResponse({"status": "ok"})


@app.get("/health")
async def health():
    return {"status": "ok", "service": "nfe-whatsapp-bot"}
