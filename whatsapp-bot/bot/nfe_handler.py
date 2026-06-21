"""
Bot NF-e - Handler de mensagens para WhatsApp.

Integra com o MCP Server (nfe-brasil) para processar
operações de nota fiscal via mensagens.
"""

import asyncio
import json
import logging
import os
from typing import Any

logger = logging.getLogger("nfe.bot")

# URL do MCP Server (configurável via env)
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://mcp-server:8000/mcp")


async def call_mcp_tool(tool_name: str, arguments: dict[str, Any]) -> dict:
    """Chama uma tool do MCP Server via HTTP."""
    import httpx

    session_id = None

    # Inicializar sessão MCP
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
        )

        # Extrair session ID
        session_id = init_resp.headers.get("mcp-session-id")
        if not session_id:
            return {"error": "Falha ao inicializar sessão MCP"}

        # Chamar tool
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
        )

        # Parsear resposta
        for line in tool_resp.text.split("\n"):
            if line.startswith("data: "):
                data = json.loads(line[6:])
                result = data.get("result", {})
                if result.get("isError"):
                    return {"error": result.get("content", [{}])[0].get("text", "Erro desconhecido")}
                return result.get("structuredContent", result.get("content", [{}]))

    return {"error": "Resposta vazia do MCP Server"}


async def processar_nfe(numero: str, texto: str) -> str:
    """Processa uma mensagem sobre NF-e e retorna resposta formatada."""
    import re

    # Chave de acesso (44 dígitos)
    digitos = re.sub(r"\D", "", texto)
    if len(digitos) == 44:
        # Consultar NF-e
        resultado = await call_mcp_tool("consultar_nfe", {"chave_acesso": digitos})
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
            f"*Valor:* R$ {total.get('vNF', '0,00')}\n"
            f"*Chave:* {digitos[:4]}...{digitos[-4:]}\n\n"
            f"Posso gerar o DANFE ou validar o XML se precisar."
        )

    # XML detectado
    if "<?xml" in texto.lower() or "<nfe" in texto.lower():
        resultado = await call_mcp_tool("parse_nfe_xml", {"xml_content": texto})
        if "error" in resultado:
            return f"Erro ao processar XML: {resultado['error']}"
        return f"XML processado com sucesso! Extraídos {len(resultado.get('itens', []))} itens."

    # Consulta SEFAZ
    if "sefaz" in texto.lower() or "status" in texto.lower():
        # Tentar extrair UF
        uf_match = re.search(r"\b([A-Z]{2})\b", texto.upper())
        if uf_match:
            uf = uf_match.group(1)
            resultado = await call_mcp_tool("consultar_status_sefaz", {"uf": uf})
            if "error" in resultado:
                return f"Erro ao consultar SEFAZ: {resultado['error']}"
            return f"Status SEFAZ {uf}: {resultado.get('status', 'N/A')}"

    # CNPJ
    cnpj_match = re.search(r"\b\d{14}\b", digitos)
    if cnpj_match:
        resultado = await call_mcp_tool("consultar_cnpj", {"cnpj": cnpj_match.group()})
        if "error" in resultado:
            return f"Erro ao consultar CNPJ: {resultado['error']}"
        return (
            f"🏢 *Consulta CNPJ*\n\n"
            f"*Razão Social:* {resultado.get('razao_social', 'N/A')}\n"
            f"*Situação:* {resultado.get('situacao_cadastral', 'N/A')}\n"
            f"*CNAE:* {resultado.get('cnae_fiscal', 'N/A')}"
        )

    return None


if __name__ == "__main__":
    # Teste rápido
    async def main():
        resultado = await processar_nfe("5511999999999", "consultar sefaz SP")
        print(resultado)

    asyncio.run(main())
