"""
WhatsApp Cloud API Bridge para NF-e.

Recebe mensagens via webhook, detecta intenção fiscal e roteia:
- Intenção NF-e → handle_nfe_message() (resposta direta)
- Geral → Hermes Agent ou resposta padrão

Porta: 3001 (configurável via PORT env)
"""

import json
import logging
import os
import re
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("nfe.whatsapp.cloud_api")

app = FastAPI(title="NFe WhatsApp Bridge")

# Configuração
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "nfe-brasil-verify")
WHATSAPP_RESTRICTED_MODE = os.getenv("WHATSAPP_RESTRICTED_MODE", "true").lower() == "true"

# Horário comercial
NFE_BUSINESS_HOUR_START = int(os.getenv("NFE_BUSINESS_HOUR_START", "8"))
NFE_BUSINESS_HOUR_END = int(os.getenv("NFE_BUSINESS_HOUR_END", "18"))
NFE_BUSINESS_DAYS = os.getenv("NFE_BUSINESS_DAYS", "0,1,2,3,4")  # seg-sex


def detectar_intencao_nfe(texto: str) -> bool:
    """Detecta se a mensagem é sobre nota fiscal."""
    texto_lower = texto.lower().strip()

    # Padrões de intenção fiscal
    padroes = [
        r"\b\d{44}\b",  # Chave de acesso 44 dígitos
        r"\bnf[-\s]?e\b",
        r"\bnfc[-\s]?e\b",
        r"\bnf[-\s]?se\b",
        r"\bct[-\s]?e\b",
        r"\bmdf[-\s]?e\b",
        r"\bnota\s+fiscal",
        r"\bdanfe\b",
        r"\bxml\b.*\bnf",
        r"\bnf\b.*\bxml\b",
        r"\bconsultar?\b.*\bnota\b",
        r"\bvalidar?\b.*\bnota\b",
        r"\bchave\s+de\s+acesso\b",
        r"\bsefaz\b",
        r"\bsimples\s+nacional\b",
        r"\bmei\b",
        r"\bsped\b",
        r"\besocial\b",
        r"\bcnpj\b.*\bconsult",
        r"\bcertid[ãa]o\b",
        r"\bsitua[çc][ãa]o\s+cadastral\b",
    ]

    for padrao in padroes:
        if re.search(padrao, texto_lower):
            return True

    # Menus numéricos (1-8)
    if texto.strip() in [str(i) for i in range(1, 9)]:
        return True

    return False


def dentro_do_horario() -> bool:
    """Verifica se está dentro do horário comercial."""
    from datetime import datetime

    now = datetime.now()
    dia_semana = now.weekday()  # 0=segunda

    if dia_semana not in [int(d) for d in NFE_BUSINESS_DAYS.split(",")]:
        return False

    if NFE_BUSINESS_HOUR_START <= now.hour < NFE_BUSINESS_HOUR_END:
        return True

    return False


def formatar_chave(texto: str) -> str | None:
    """Tenta extrair e formatar uma chave de acesso de 44 dígitos."""
    digitos = re.sub(r"\D", "", texto)
    if len(digitos) == 44:
        return " ".join(digitos[i : i + 4] for i in range(0, 44, 4))
    return None


# Respostas naturais (modo restrito)
RESPOSTAS = {
    "menu_principal": (
        "Olá! Sou o assistente de notas fiscais. "
        "Posso ajudar com:\n"
        "• Consulta de NF-e por chave de acesso\n"
        "• Validação de XML\n"
        "• Status na SEFAZ\n"
        "• Geração de DANFE\n"
        "• Consulta de CNPJ\n\n"
        "Envie sua chave de 44 dígitos ou digite o que precisa!"
    ),
    "chave_recebida": (
        "Recebi sua chave! Com ela posso consultar o status da nota "
        "na SEFAZ, gerar o DANFE ou validar o XML. O que você prefere?"
    ),
    "chave_invalida": (
        "Essa chave não parece válida. Pode verificar e tentar de novo? "
        "A chave deve ter 44 dígitos."
    ),
    "xml_recebido": (
        "Recebi o XML! É uma nota emitida por {emitente} no valor de "
        "R$ {valor}, destinada a {destinatario}. {status}"
    ),
    "fora_do_escopo": (
        "Desculpe, no momento só posso ajudar com notas fiscais. "
        "Envie uma chave de acesso, XML ou pergunte sobre NF-e."
    ),
    "fora_horario": (
        "Nosso horário de atendimento é das {inicio}h às {fim}h. "
        "Aguarde retorno!"
    ),
    "erro": (
        "Houve um erro ao processar sua solicitação. "
        "Pode tentar novamente?"
    ),
}


async def enviar_whatsapp(numero: str, mensagem: str) -> bool:
    """Envia mensagem via WhatsApp Cloud API."""
    if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_ID:
        logger.warning("WhatsApp não configurado (token/phone_id ausente)")
        return False

    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": mensagem},
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            logger.error("WhatsApp API erro %d: %s", resp.status_code, resp.text)
            return False
        return True


async def handle_nfe_message(numero: str, texto: str) -> str:
    """Processa mensagem fiscal e retorna resposta."""
    # Fora do horário
    if not dentro_do_horario():
        return RESPOSTAS["fora_horario"].format(
            inicio=NFE_BUSINESS_HOUR_START,
            fim=NFE_BUSINESS_HOUR_END,
        )

    # Chave de acesso (44 dígitos)
    chave = formatar_chave(texto)
    if chave:
        return RESPOSTAS["chave_recebida"]

    # XML (detecta por conteúdo)
    if "<?xml" in texto.lower() or "<nfe" in texto.lower():
        # TODO: parsear XML e extrair dados
        return "Recebi o XML! Processando..."

    # Menus numéricos
    if texto.strip() == "1":
        return "Envie a chave de acesso da nota fiscal (44 dígitos)."
    if texto.strip() == "2":
        return "Envie o XML da nota fiscal para validação."
    if texto.strip() == "3":
        return "Informe aUF (sigla do estado) para consultar a SEFAZ."
    if texto.strip() == "4":
        return "Envie o XML para gerar o DANFE em PDF."
    if texto.strip() == "5":
        return "Envie o CNPJ para consulta."
    if texto.strip() == "6":
        return "Informe o número da NFS-e e o município."
    if texto.strip() == "7":
        return "Envie o conteúdo do arquivo SPED."
    if texto.strip() == "8":
        return "Por favor, aguarde um atendente."

    # Menu principal
    return RESPOSTAS["menu_principal"]


@app.get("/webhook")
async def webhook_verify(request: Request):
    """Verificação do webhook (Meta)."""
    params = dict(request.query_params)
    if params.get("hub.verify_token") == WHATSAPP_VERIFY_TOKEN:
        return JSONResponse({"challenge": params.get("hub.challenge", "")})
    return JSONResponse({"error": "Verify token inválido"}, status_code=403)


@app.post("/webhook")
async def webhook_receive(request: Request):
    """Recebe mensagens do WhatsApp."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "JSON inválido"}, status_code=400)

    # Extrair mensagem
    try:
        entry = body["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "messages" not in value:
            return JSONResponse({"status": "ok"})

        msg = value["messages"][0]
        numero = msg["from"]
        texto = msg.get("text", {}).get("body", "")

        if not texto:
            return JSONResponse({"status": "ok"})

        logger.info("Mensagem recebida de %s: %s", numero, texto[:50])

        # Detectar intenção
        if detectar_intencao_nfe(texto):
            resposta = await handle_nfe_message(numero, texto)
            await enviar_whatsapp(numero, resposta)
        elif WHATSAPP_RESTRICTED_MODE:
            await enviar_whatsapp(numero, RESPOSTAS["fora_do_escopo"])
        else:
            # TODO: encaminhar para Hermes Agent
            logger.info("Encaminhando para Hermes: %s", texto[:50])

    except (KeyError, IndexError) as e:
        logger.error("Erro ao processar webhook: %s", e)

    return JSONResponse({"status": "ok"})


@app.get("/health")
async def health():
    return {"status": "ok", "service": "nfe-whatsapp-bridge"}
