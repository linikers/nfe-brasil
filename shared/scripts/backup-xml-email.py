#!/usr/bin/env python3
"""
Backup de XMLs de NF-e via email (IMAP).

Baixa XMLs de notas fiscais anexados em emails da caixa de entrada.
"""

import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
import os
import sys


def baixar_xmls_nfe_do_email(
    email_user: str,
    email_pass: str,
    imap_server: str = "imap.gmail.com",
    output_dir: str = "./xmls_nfe",
    dias_para_tras: int = 7,
) -> int:
    """Baixa XMLs de NF-e anexados em emails."""
    os.makedirs(output_dir, exist_ok=True)

    mail = imaplib.IMAP4_SSL(imap_server)
    mail.login(email_user, email_pass)
    mail.select("INBOX")

    datailtro = (datetime.now() - timedelta(dias=dias_para_tras)).strftime("%d-%b-%Y")
    status, ids = mail.search(None, f'(SINCE {datailtro} SUBJECT "NF-e")')

    contador = 0
    for msg_id in ids[0].split():
        status, data = mail.fetch(msg_id, "(RFC822)")
        msg = email.message_from_bytes(data[0][1])

        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            filename = part.get_filename()
            if filename and filename.lower().endswith(".xml"):
                payload = part.get_payload(decode=True)
                filepath = os.path.join(output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(payload)
                contador += 1
                print(f"Baixado: {filename}")

    mail.close()
    mail.logout()
    return contador


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python backup-xml-email.py <email> <senha> [imap_server] [dias]")
        print("Exemplo: python backup-xml-email.py user@gmail.com senha 7")
        sys.exit(1)

    email_user = sys.argv[1]
    email_pass = sys.argv[2]
    imap_server = sys.argv[3] if len(sys.argv) > 3 else "imap.gmail.com"
    dias = int(sys.argv[4]) if len(sys.argv) > 4 else 7

    total = baixar_xmls_nfe_do_email(email_user, email_pass, imap_server, dias_para_tras=dias)
    print(f"\nTotal: {total} XMLs baixados")
