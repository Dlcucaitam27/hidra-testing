import secrets
import string
import hashlib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

_BOGOTA = ZoneInfo("America/Bogota")

# Almacén temporal en memoria: {username: {code, expires_at}}
_codigos_pendientes: dict = {}

_DOMINIO = "@unp.gov.co"
_EXPIRACION_MINUTOS = 15


def username_a_email(username: str) -> str:
    """Convierte nombre.apellido → nombre.apellido@unp.gov.co"""
    return f"{username.strip().lower()}{_DOMINIO}"


def generar_codigo() -> str:
    """Genera un código numérico de 6 dígitos criptográficamente seguro."""
    return "".join(secrets.choice(string.digits) for _ in range(6))


def guardar_codigo(username: str, codigo: str):
    """Guarda el código con expiración de 15 minutos."""
    _codigos_pendientes[username] = {
        "code": codigo,
        "expires_at": datetime.now(tz=_BOGOTA) + timedelta(minutes=_EXPIRACION_MINUTOS),
    }


def validar_codigo(username: str, codigo: str) -> bool:
    """Retorna True si el código es correcto y no ha expirado."""
    entrada = _codigos_pendientes.get(username)
    if not entrada:
        return False
    if datetime.now(tz=_BOGOTA) > entrada["expires_at"]:
        _codigos_pendientes.pop(username, None)
        return False
    return entrada["code"] == codigo.strip()


def limpiar_codigo(username: str):
    """Elimina el código después de usarlo."""
    _codigos_pendientes.pop(username, None)


def enviar_codigo_recuperacion(username: str) -> tuple[bool, str]:
    """
    Genera un código y lo envía al correo institucional del usuario.
    Retorna (éxito: bool, mensaje: str).
    Requiere en st.secrets:
        [email]
        smtp_host = "smtp.office365.com"   # o smtp.gmail.com
        smtp_port = 587
        sender    = "noreply@unp.gov.co"
        password  = "..."
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    import streamlit as st

    codigo = generar_codigo()
    guardar_codigo(username, codigo)
    destinatario = username_a_email(username)

    try:
        cfg = st.secrets.get("email", {})
        smtp_host = cfg.get("smtp_host", "smtp.office365.com")
        smtp_port = int(cfg.get("smtp_port", 587))
        sender    = cfg.get("sender", "")
        password  = cfg.get("password", "")

        if not sender or not password:
            # Modo desarrollo: muestra el código en consola
            print(f"[RECOVERY] Código para {username}: {codigo}")
            return True, destinatario

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "🔐 Recuperación de contraseña — Sistema ISMR"
        msg["From"]    = sender
        msg["To"]      = destinatario

        cuerpo_html = f"""
        <html><body style="font-family:Arial,sans-serif;background:#0f0f0f;color:#f0f0f0;padding:32px;">
          <div style="max-width:480px;margin:0 auto;background:#1a1a1a;border-radius:8px;
                      padding:32px;border:1px solid #333;">
            <h2 style="color:#4F8BFF;margin-top:0;">Sistema ISMR</h2>
            <p>Hola <strong>{username}</strong>,</p>
            <p>Recibimos una solicitud para restablecer tu contraseña.</p>
            <p>Tu código de verificación es:</p>
            <div style="text-align:center;margin:24px 0;">
              <span style="font-size:36px;font-weight:bold;letter-spacing:12px;
                           color:#4F8BFF;background:#0d1f3c;padding:12px 24px;
                           border-radius:6px;">{codigo}</span>
            </div>
            <p style="color:#888;font-size:13px;">
              Este código expira en <strong>{_EXPIRACION_MINUTOS} minutos</strong>.<br>
              Si no solicitaste este cambio, ignora este mensaje.
            </p>
            <hr style="border-color:#333;">
            <p style="color:#555;font-size:11px;margin-bottom:0;">
              Sistema ISMR — Unidad Nacional de Protección
            </p>
          </div>
        </body></html>
        """

        msg.attach(MIMEText(cuerpo_html, "html"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, destinatario, msg.as_string())

        return True, destinatario

    except Exception as e:
        limpiar_codigo(username)
        return False, str(e)
