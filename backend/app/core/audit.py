"""Process-local signed reports. A signature seals a record, not the truth of its claims."""

import base64
import hashlib
import json
from collections import OrderedDict
from datetime import datetime, timezone
from io import BytesIO
from threading import RLock
from time import monotonic
from uuid import uuid4
from xml.sax.saxutils import escape

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer


class ExpiringStore:
    """Bounded volatile storage: no files, raw media, embeddings or durable identifiers."""
    def __init__(self, maximum=128, ttl=3600):
        self.maximum, self.ttl = maximum, ttl
        self._items, self._lock = OrderedDict(), RLock()

    def put(self, key, value):
        with self._lock:
            self._items[key] = (monotonic(), value)
            self._items.move_to_end(key)
            while len(self._items) > self.maximum:
                self._items.popitem(last=False)

    def get(self, key):
        with self._lock:
            expired = [k for k, (created, _) in self._items.items() if monotonic() - created > self.ttl]
            for old in expired:
                self._items.pop(old)
            entry = self._items.get(key)
            if entry:
                self._items.move_to_end(key)
                return entry[1]
            return None


cases = ExpiringStore()
certificates = ExpiringStore(maximum=64)
_signing_key = Ed25519PrivateKey.generate()
PUBLIC_KEY = base64.b64encode(_signing_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()


def canonical(record):
    return json.dumps(record, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode()


def create_certificate(verdict, sign_request, public_base_url):
    certificate_id = "cert_" + uuid4().hex
    timestamp = datetime.now(timezone.utc).isoformat()
    verify_url = f"{public_base_url}/api/v1/certificates/{certificate_id}/verify"
    payload = {"certificateId": certificate_id, "timestamp": timestamp,
        "verdict": verdict.model_dump(mode="json"), "analystStatement": sign_request.model_dump(mode="json"),
        "scope": "Local analyst attestation; analyst identity and conclusions are not independently authenticated."}
    encoded = canonical(payload)
    payload_hash = hashlib.sha256(encoded).hexdigest()
    signature = base64.b64encode(_signing_key.sign(encoded)).decode()
    output = BytesIO()
    document = SimpleDocTemplate(output, title="TrustGuard incident record", author="TrustGuard Local Engine")
    styles = getSampleStyleSheet()
    story = []

    def paragraph(value, style="BodyText"):
        story.append(Paragraph(escape(str(value)), styles[style]))
        story.append(Spacer(1, 8))

    paragraph("TrustGuard | Sealed incident record", "Title")
    paragraph(certificate_id)
    paragraph(timestamp)
    paragraph("NO SCORE IS PROOF. This certificate seals an analyst's statement and a heuristic assessment. It does not certify authenticity or wrongdoing.")
    if verdict.innovationMetadata.get("simulation") == "true":
        paragraph("SYNTHETIC DEMONSTRATION FIXTURE - not an observed real-world incident.", "Heading2")
    paragraph(verdict.verdictSummary.headline, "Heading2")
    for key, value in verdict.calibratedTrustVector.model_dump().items():
        paragraph(f"{key}: {value:.3f}")
    paragraph("Evidence ledger", "Heading2")
    for item in verdict.evidenceLedger:
        paragraph(f"[{item.polarity.value}] {item.finding}")
    paragraph("Human verification statement", "Heading2")
    paragraph(f"Analyst: {sign_request.analystId}; decision: {sign_request.finalDecision}")
    paragraph(sign_request.analystNotes)
    paragraph("Completed playbook steps: " + ", ".join(map(str, sign_request.completedSteps)))
    paragraph("Cryptographic verification", "Heading2")
    paragraph(f"SHA-256 of canonical signed payload: {payload_hash}")
    paragraph(f"Ed25519 signature (base64): {signature}")
    paragraph(f"Session public key (base64): {PUBLIC_KEY}")
    paragraph("The local signing key and records expire when the server restarts. Records also expire after one hour or cache eviction. The key is not an external trust authority.")
    paragraph(verify_url)
    qr = QrCodeWidget(verify_url)
    x0, y0, x1, y1 = qr.getBounds()
    drawing = Drawing(125, 125, transform=[125 / (x1 - x0), 0, 0, 125 / (y1 - y0), 0, 0])
    drawing.add(qr)
    story.append(drawing)
    document.build(story)
    pdf = output.getvalue()
    entry = {"payload": payload, "payloadSha256": payload_hash, "signature": signature,
             "publicKey": PUBLIC_KEY, "pdf": pdf, "certificateSha256": hashlib.sha256(pdf).hexdigest(),
             "verifyUrl": verify_url, "timestamp": timestamp}
    # A second, detached seal binds the final PDF bytes without a circular PDF hash.
    manifest = {key: entry[key] for key in ("payloadSha256", "certificateSha256", "publicKey")}
    entry["manifestSignature"] = base64.b64encode(_signing_key.sign(canonical(manifest))).decode()
    certificates.put(certificate_id, entry)
    return certificate_id, entry


def verify_certificate(entry):
    encoded = canonical(entry["payload"])
    try:
        _signing_key.public_key().verify(base64.b64decode(entry["signature"]), encoded)
        manifest = {key: entry[key] for key in ("payloadSha256", "certificateSha256", "publicKey")}
        _signing_key.public_key().verify(base64.b64decode(entry["manifestSignature"]), canonical(manifest))
        signature_valid = True
    except (InvalidSignature, ValueError):
        signature_valid = False
    return signature_valid and entry["publicKey"] == PUBLIC_KEY and hashlib.sha256(encoded).hexdigest() == entry["payloadSha256"] and hashlib.sha256(entry["pdf"]).hexdigest() == entry["certificateSha256"]
