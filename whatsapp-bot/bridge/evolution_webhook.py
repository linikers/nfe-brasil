"""
WhatsApp Webhook Handler - Evolution API.

Recebe webhooks da Evolution API e processa mensagens NF-e.
Também suporta envio de mensagens via Evolution API.
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
NFE_BUSINESS_DAYS = os.getenv("NFE_BUSINESS_DAYS", "0,1,2,3,4")  # seg-sex


# ---------------------------------------------------------------------------
# Detecção de intenção fiscal
# ---------------------------------------------------------------------------

def detectar_intencao_nfe(texto: str) -> bool:
    """Detecta se a mensagem é sobre nota fiscal."""
    texto_lower = texto.lower().strip()

    padroes = [
        r"\b\d{44}\b",           # Chave de acesso
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
    """Extrai chave de 44 dígitos do texto."""
    digitos = re.sub(r"\D", "", texto)
    if len(digitos) == 44:
        return digitos
    return None


# ---------------------------------------------------------------------------
# Envio de mensagens via Evolution API
# ---------------------------------------------------------------------------

async def enviar_whatsapp(numero: str, mensagem: str, instance: str = "nfe-brasil") -> bool:
    """Envia mensagem via Evolution API."""
    if not EVOLUTION_API_KEY:
        logger.warning("Evolution API não configurada")
        return False

    url = f"{EVOLUTION_API_URL}/message/sendText/{instance}"
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "number": numero,
        "text": mensagem,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code not in (200, 201):
            logger.error("Evolution API erro %d: %s", resp.status_code, resp.text[:200])
            return False
        return True


async def enviar_whatsapp_arquivo(numero: str, caminho: str, instance: str = "nfe-brasil") -> bool:
    """Envia arquivo (PDF, XML) via Evolution API."""
    if not EVOLUTION_API_KEY:
        return False

    url = f"{EVOLUTION_API_URL}/message/sendFile/{instance}"
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "number": numero,
        "filePath": caminho,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers, timeout=60)
        return resp.status_code in (200, 201)


# ---------------------------------------------------------------------------
# Processamento de mensagens NF-e
# ---------------------------------------------------------------------------

async def call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> dict:
    """Chama uma tool do MCP Server."""
    import json

    async with httpx.AsyncClient() as client:
        # Initialize
        init_resp = await client.post(
            MCP_SERVER_URL,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "whatsapp-bot", "version": "1.0"},
                },
            },
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            timeout=30,
        )

        session_id = init_resp.headers.get("mcp-session-id")
        if not session_id:
            return {"error": "Falha ao inicializar sessão MCP"}

        # Call tool
        tool_resp = await client.post(
            MCP_SERVER_URL,
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
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
                    return {"error": result.get("content", [{}])[0].get("text", "Erro")}
                return result.get("structuredContent", result.get("content", [{}]))

    return {"error": "Resposta vazia do MCP Server"}


async def processar_nfe(texto: str) -> str | None:
    """Processa mensagem fiscal e retorna resposta."""

    # Fora do horário
    if not dentro_do_horario():
        return (
            f"Nosso horário de atendimento é das {NFE_BUSINESS_HOUR_START}h "
            f"às {NFE_BUSINESS_HOUR_END}h. Aguarde retorno!"
        )

    # Chave de acesso (44 dígitos)
    chave = formatar_chave(texto)
    if chave:
        resultado = await call_mcp_tool("consultar_nfe", {"chave_acesso": chave})
        if "error" in resultado:
            return f"Não foi possível consultar a nota: {resultado['error']}"

        emitente = resultado.get("emitente", {})
        destinatario = resultado.get("destinatario", {})
        total = resultado.get("total", {})

        return (
            f"📋 *NF-e Consultada*\n\n"
            f"*Emitente:* {emitente.get('xNome', 'N/A')}\n"
            f"*CNPJ:* {emitente.get('cnpj', 'N/A')}\n"
            f"*Destinatário:* {destinatario.get('xNome', 'N/A')}\n"
            f"*Valor:* R$ {total.get('vNF', '0,00')}\n\n"
            f"Posso gerar o DANFE ou validar o XML se precisar."
        )

    # XML
    if "<?xml" in texto.lower() or "<nfe" in texto.lower():
        resultado = await call_mcp_tool("parse_nfe_xml", {"xml_content": texto})
        if "error" in resultado:
            return f"Erro ao processar XML: {resultado['error']}"
        return "XML processado com sucesso!"

    # Consulta CNPJ
    cnpj_match = re.search(r"\b\d{14}\b", re.sub(r"\D", "", texto))
    if cnpj_match:
        resultado = await call_mcp_tool("consultar_cnpj", {"cnpj": cnpj_match.group()})
        if "error" not in resultado:
            return (
                f"🏢 *Consulta CNPJ*\n\n"
                f"*Razão Social:* {resultado.get('razao_social', 'N/A')}\n"
                f"*Situação:* {resultado.get('situacao_cadastral', 'N/A')}"
            )

    # Menu
    return (
        "Olá! Sou o assistente de notas fiscais.\n\n"
        "Posso ajudar com:\n"
        "• Consulta de NF-e (envie a chave de 44 dígitos)\n"
        "• Validação de XML\n"
        "• Consulta de CNPJ\n"
        "• Status na SEFAZ\n\n"
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

    # Evolution API envia differentes tipos de evento
    event = body.get("event", "")

    # Só processar mensagens recebidas
    if event not in ("messages.upsert", "messages.set"):
        return JSONResponse({"status": "ok"})

    # Extrair dados da mensagem
    data = body.get("data", {})
    instance = body.get("instance", "nfe-brasil")

    # Ignorar mensagens enviadas por nós
    if data.get("key", {}).get("fromMe", False):
        return JSONResponse({"status": "ok"})

    # Ignorar mensagens de grupo
    if data.get("key", {}).get("remoteJid", "").endswith("@g.us"):
        return JSONResponse({"status": "ok"})

    # Extrair texto
    texto = data.get("message", {}).get("conversation", "")
    if not texto:
        texto = data.get("message", {}).get("extendedTextMessage", {}).get("text", "")

    if not texto:
        return JSONResponse({"status": "ok"})

    # Número do remetente
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
            "Desculpe, no momento só posso ajudar com notas fiscais. "
            "Envie uma chave de acesso ou pergunte sobre NF-e.",
            instance,
        )

    return JSONResponse({"status": "ok"})


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "nfe-whatsapp-bot",
        "evolution_api": EVOLUTION_API_URL,
        "mcp_server": MCP_SERVER_URL,
    }
