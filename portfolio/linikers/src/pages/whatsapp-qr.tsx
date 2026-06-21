import { useState, useEffect, useCallback } from "react";
import {
  Box,
  Typography,
  Container,
  CircularProgress,
  Alert,
  Chip,
  IconButton,
} from "@mui/material";
import { QrCode2, Refresh, CheckCircle, Error } from "@mui/icons-material";

const EVOLUTION_API = "http://2.24.115.130:8085";
const API_KEY = "nfe-br...ey";
const INSTANCE = "nfe-brasil";

export default function WhatsAppQR() {
  const [qrCode, setQrCode] = useState<string | null>(null);
  const [status, setStatus] = useState<"loading" | "waiting" | "connected" | "error">("loading");
  const [errorMsg, setErrorMsg] = useState("");
  const [countdown, setCountdown] = useState(30);

  const fetchQR = useCallback(async () => {
    try {
      // Buscar status da instância
      const statusResp = await fetch(`${EVOLUTION_API}/instance/connectionState/${INSTANCE}`, {
        headers: { apikey: API_KEY },
      });

      if (statusResp.ok) {
        const statusData = await statusResp.json();
        const state = statusData?.instance?.state || statusData?.state;

        if (state === "open") {
          setStatus("connected");
          setQrCode(null);
          return;
        }
      }

      // Buscar QR code
      const qrResp = await fetch(`${EVOLUTION_API}/instance/connect/${INSTANCE}`, {
        headers: { apikey: API_KEY },
      });

      if (qrResp.ok) {
        const qrData = await qrResp.json();
        const base64 = qrData?.base64 || qrData?.qr || qrData?.code;

        if (base64) {
          // Se já é data URL, usa direto. Se não, adiciona prefixo
          const imgSrc = base64.startsWith("data:")
            ? base64
            : `data:image/png;base64,${base64}`;

          setQrCode(imgSrc);
          setStatus("waiting");
          setCountdown(30);
        } else {
          setStatus("waiting");
          setErrorMsg("Aguardando QR code do servidor...");
        }
      } else {
        setStatus("error");
        setErrorMsg(`Erro ao conectar: HTTP ${qrResp.status}`);
      }
    } catch (err: any) {
      setStatus("error");
      setErrorMsg(`Erro de conexão: ${err.message}`);
    }
  }, []);

  // Buscar QR code ao montar
  useEffect(() => {
    fetchQR();
  }, [fetchQR]);

  // Auto-refresh a cada 30 segundos
  useEffect(() => {
    if (status === "connected") return;

    const interval = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          fetchQR();
          return 30;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [status, fetchQR]);

  return (
    <Container
      maxWidth="sm"
      sx={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        bgcolor: "#0a0a0a",
        py: 4,
      }}
    >
      <QrCode2 sx={{ fontSize: 48, color: "#25D366", mb: 1 }} />

      <Typography
        variant="h4"
        sx={{
          fontFamily: "monospace",
          fontWeight: 900,
          color: "#fff",
          fontSize: "1.2rem",
          mb: 0.5,
        }}
      >
        whatsapp-qr/
      </Typography>

      <Typography
        variant="body2"
        sx={{
          color: "text.secondary",
          fontFamily: "monospace",
          fontSize: "0.75rem",
          mb: 3,
        }}
      >
        escaneie para conectar o dispositivo
      </Typography>

      {/* Status */}
      <Box sx={{ mb: 3 }}>
        {status === "loading" && (
          <Chip
            icon={<CircularProgress size={14} />}
            label="Conectando ao servidor..."
            sx={{ bgcolor: "#1a1a2e", color: "#fff" }}
          />
        )}
        {status === "waiting" && (
          <Chip
            icon={<QrCode2 sx={{ color: "#25D366" }} />}
            label={`Aguardando scan • ${countdown}s`}
            sx={{ bgcolor: "#1a1a2e", color: "#fff" }}
          />
        )}
        {status === "connected" && (
          <Chip
            icon={<CheckCircle sx={{ color: "#25D366" }} />}
            label="Conectado!"
            sx={{ bgcolor: "#1a2e1a", color: "#25D366" }}
          />
        )}
        {status === "error" && (
          <Chip
            icon={<Error sx={{ color: "#f44336" }} />}
            label={errorMsg}
            sx={{ bgcolor: "#2e1a1a", color: "#f44336" }}
          />
        )}
      </Box>

      {/* QR Code */}
      <Box
        sx={{
          width: 280,
          height: 280,
          bgcolor: "#fff",
          borderRadius: 3,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
          boxShadow: "0 0 40px rgba(37, 211, 102, 0.15)",
          border: "2px solid #25D366",
        }}
      >
        {status === "connected" ? (
          <Box sx={{ textAlign: "center" }}>
            <CheckCircle sx={{ fontSize: 64, color: "#25D366" }} />
            <Typography
              sx={{
                color: "#333",
                fontFamily: "monospace",
                mt: 1,
                fontWeight: 700,
              }}
            >
              WhatsApp Conectado
            </Typography>
          </Box>
        ) : qrCode ? (
          <img
            src={qrCode}
            alt="WhatsApp QR Code"
            style={{
              width: 250,
              height: 250,
              objectFit: "contain",
            }}
          />
        ) : (
          <Box sx={{ textAlign: "center", p: 2 }}>
            <CircularProgress sx={{ color: "#25D366" }} />
            <Typography
              sx={{
                color: "#666",
                fontFamily: "monospace",
                mt: 2,
                fontSize: "0.8rem",
              }}
            >
              Gerando QR code...
            </Typography>
          </Box>
        )}

        {/* Botão refresh */}
        {status !== "connected" && (
          <IconButton
            onClick={fetchQR}
            sx={{
              position: "absolute",
              top: -12,
              right: -12,
              bgcolor: "#25D366",
              "&:hover": { bgcolor: "#1da851" },
            }}
            size="small"
          >
            <Refresh sx={{ color: "#000", fontSize: 18 }} />
          </IconButton>
        )}
      </Box>

      {/* Instruções */}
      <Box
        sx={{
          mt: 4,
          p: 2,
          bgcolor: "#111",
          borderRadius: 2,
          border: "1px solid #222",
          maxWidth: 380,
          width: "100%",
        }}
      >
        <Typography
          variant="body2"
          sx={{
            color: "#aaa",
            fontFamily: "monospace",
            fontSize: "0.8rem",
            lineHeight: 1.8,
          }}
        >
          <span style={{ color: "#25D366" }}>1.</span> Abra WhatsApp no
          celular
          <br />
          <span style={{ color: "#25D366" }}>2.</span> Configurações →
          Aparelhos conectados
          <br />
          <span style={{ color: "#25D366" }}>3.</span> Conectar aparelho
          <br />
          <span style={{ color: "#25D366" }}>4.</span> Escaneie o QR code
          acima
          <br />
          <span style={{ color: "#25D366" }}>5.</span> QR renova
          automaticamente
        </Typography>
      </Box>

      {/* Info técnica */}
      <Typography
        variant="body2"
        sx={{
          color: "#555",
          fontFamily: "monospace",
          fontSize: "0.65rem",
          mt: 2,
        }}
      >
        nfe-brasil • port 8085 • auto-refresh 30s
      </Typography>
    </Container>
  );
}
