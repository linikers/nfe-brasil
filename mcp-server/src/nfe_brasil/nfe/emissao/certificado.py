"""Leitura e validacao do certificado digital A1 (PKCS#12 / .pfx)."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    pkcs12,
)
from cryptography.x509.oid import NameOID


class CertificadoError(ValueError):
    """Certificado ausente, senha incorreta ou arquivo invalido."""


@dataclass(frozen=True)
class InfoCertificado:
    """Dados do titular extraidos do certificado."""

    titular: str
    cnpj: str | None
    cpf: str | None
    valido_de: datetime
    valido_ate: datetime
    autoridade_certificadora: str
    dias_para_expirar: int
    expirado: bool


class CertificadoA1:
    """Certificado A1 carregado do arquivo .pfx com a senha."""

    def __init__(self, caminho: str | Path, senha: str) -> None:
        self.caminho = Path(caminho).expanduser()
        if not self.caminho.is_file():
            raise CertificadoError(f"Arquivo de certificado nao encontrado: {self.caminho}")

        conteudo = self.caminho.read_bytes()
        try:
            chave, cert, _extras = pkcs12.load_key_and_certificates(
                conteudo, senha.encode("utf-8") if senha else None
            )
        except Exception as exc:  # senha errada, arquivo corrompido, formato invalido
            raise CertificadoError(
                "Nao foi possivel abrir o certificado. Senha incorreta ou arquivo invalido."
            ) from exc

        if chave is None or cert is None:
            raise CertificadoError("O arquivo nao contem chave privada e certificado")

        self._chave = chave
        self._cert = cert
        self._pfx = conteudo

    @property
    def chave_pem(self) -> bytes:
        return self._chave.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())

    @property
    def certificado_pem(self) -> bytes:
        return self._cert.public_bytes(Encoding.PEM)

    @property
    def certificado_der(self) -> bytes:
        return self._cert.public_bytes(Encoding.DER)

    def info(self) -> InfoCertificado:
        atributos = {a.oid: a.value for a in self._cert.subject}
        cn = atributos.get(NameOID.COMMON_NAME, "")
        digitos = "".join(c for c in str(cn) if c.isdigit())

        cnpj = digitos if len(digitos) == 14 else None
        cpf = digitos if len(digitos) == 11 else None

        valido_de = self._cert.not_valid_before_utc
        valido_ate = self._cert.not_valid_after_utc
        agora = datetime.now(timezone.utc)
        dias = (valido_ate - agora).days

        return InfoCertificado(
            titular=str(cn),
            cnpj=cnpj,
            cpf=cpf,
            valido_de=valido_de,
            valido_ate=valido_ate,
            autoridade_certificadora=self._cert.issuer.rfc4514_string(),
            dias_para_expirar=dias,
            expirado=dias < 0,
        )

    def escrever_pem(self, diretorio: str | Path | None = None) -> tuple[Path, Path]:
        """Grava cert.pem e key.pem (0600) para uso em TLS mutual auth."""
        destino = Path(diretorio) if diretorio else Path(tempfile.mkdtemp(prefix="nfe-cert-"))
        destino.mkdir(parents=True, exist_ok=True)
        os.chmod(destino, 0o700)

        cert_path = destino / "certificado.pem"
        key_path = destino / "chave.pem"
        cert_path.write_bytes(self.certificado_pem)
        key_path.write_bytes(self.chave_pem)
        os.chmod(cert_path, 0o600)
        os.chmod(key_path, 0o600)
        return cert_path, key_path
