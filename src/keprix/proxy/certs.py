"""Local CA certificate generation for HTTPS MITM on matched routes."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from keprix.proxy.paths import proxy_ca_dir


def _ca_paths() -> tuple[Path, Path, Path]:
    base = proxy_ca_dir()
    return base / "ca.crt", base / "ca.key", base / "hosts"


def ensure_ca_material() -> tuple[Path, Path]:
    ca_cert_path, ca_key_path, hosts_dir = _ca_paths()
    hosts_dir.mkdir(parents=True, exist_ok=True)
    if ca_cert_path.is_file() and ca_key_path.is_file():
        return ca_cert_path, ca_key_path

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, "Keprix Credential Proxy CA"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Keprix"),
        ]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1))
        .not_valid_after(dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(key, hashes.SHA256())
    )
    ca_cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    ca_key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    ca_cert_path.chmod(0o644)
    ca_key_path.chmod(0o600)
    return ca_cert_path, ca_key_path


def host_cert_paths(host: str) -> tuple[Path, Path]:
    _, _, hosts_dir = _ca_paths()
    safe = host.replace("*", "_").replace(":", "_")
    return hosts_dir / f"{safe}.crt", hosts_dir / f"{safe}.key"


def ensure_host_certificate(host: str) -> tuple[Path, Path]:
    cert_path, key_path = host_cert_paths(host)
    if cert_path.is_file() and key_path.is_file():
        return cert_path, key_path

    ca_cert_path, ca_key_path = ensure_ca_material()
    ca_key = serialization.load_pem_private_key(ca_key_path.read_bytes(), password=None)
    ca_cert = x509.load_pem_x509_certificate(ca_cert_path.read_bytes())

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, host)])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1))
        .not_valid_after(dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=825))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName(host)]),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    cert_path.chmod(0o644)
    key_path.chmod(0o600)
    return cert_path, key_path
