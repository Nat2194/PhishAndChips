import secrets
import string
import os
import re
from datetime import datetime, timedelta

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa, dh
    from cryptography.hazmat.primitives import serialization
except ImportError:
    print("Erreur: le module 'cryptography' est requis.")
    exit(1)


def generate_play_secret(length=64):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for i in range(length))


def update_conf_secret(filepath, env_var):
    """Remplace la clé secrète codée en dur par une variable d'environnement HOCON"""
    if not os.path.exists(filepath):
        print(f"⚠️ Fichier introuvable : {filepath}")
        return

    with open(filepath, "r") as f:
        content = f.read()

    # Remplace play.http.secret.key="..." par play.http.secret.key=${?ENV_VAR}
    new_content = re.sub(
        r'play\.http\.secret\.key\s*=\s*".*?"',
        f"play.http.secret.key=${{?{env_var}}}",
        content,
    )

    with open(filepath, "w") as f:
        f.write(new_content)


def generate_ssl_cert(cert_path="ssl/cert.pem", key_path="ssl/key.pem"):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "PhishAndChips Local Dev"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName("localhost"), x509.DNSName("127.0.0.1")]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    with open(key_path, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))


def generate_dhparams(dh_path="ssl/dhparams.pem"):
    parameters = dh.generate_parameters(generator=2, key_size=2048)
    dh_bytes = parameters.parameter_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.ParameterFormat.PKCS3
    )
    with open(dh_path, "wb") as f:
        f.write(dh_bytes)


# ==========================================
# EXECUTION
# ==========================================
os.makedirs("ssl", exist_ok=True)

print("Vérification des secrets d'environnement...")
if not os.path.exists(".env"):
    env_content = f"""# Fichier auto-généré par init_secrets.py
THEHIVE_SECRET={generate_play_secret(64)}
CORTEX_SECRET={generate_play_secret(64)}
MYSQL_ROOT_PASSWORD={secrets.token_hex(16)}
MISP_BASEURL=https://localhost
"""
    with open(".env", "w") as f:
        f.write(env_content)
    print("✅ Fichier .env généré !")

    # Mise à jour automatique des fichiers .conf locaux
    print("Mise à jour des fichiers application.conf...")
    update_conf_secret("thehive/application.conf", "THEHIVE_SECRET")
    update_conf_secret("cortex/application.conf", "CORTEX_SECRET")
    print("✅ Fichiers application.conf patchés avec succès !")
else:
    print("✅ Fichier .env déjà existant, ignoré.")

print("Vérification des certificats TLS/SSL...")
if not (os.path.exists("ssl/cert.pem") and os.path.exists("ssl/key.pem")):
    generate_ssl_cert()
    print("✅ Fichiers cert.pem et key.pem générés !")
else:
    print("✅ Fichiers cert.pem et key.pem déjà existants, ignorés.")

print("Vérification des paramètres Diffie-Hellman...")
if not os.path.exists("ssl/dhparams.pem"):
    generate_dhparams()
    print("✅ Fichier dhparams.pem généré !")
else:
    print("✅ Fichier dhparams.pem déjà existant, ignoré.")
