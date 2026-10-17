"""Tamper-evident evidence chain: SHA-256 of the raw file bytes + hash links + HMAC signatures.
Saved to data/chain.json so it survives restarts."""
import datetime as dt
import hashlib
import hmac
import json
from pathlib import Path
from .config import CHAIN_JSON, SECRET


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _block_hash(core):
    return hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest()


def _sign(h):
    return hmac.new(SECRET, h.encode(), hashlib.sha256).hexdigest()


class EvidenceChain:
    def __init__(self, path=CHAIN_JSON):
        self.path = Path(path)
        self.blocks = []

    @classmethod
    def load(cls, path=CHAIN_JSON):
        c = cls(path)
        if c.path.exists():
            c.blocks = json.loads(c.path.read_text())
        return c

    def save(self):
        self.path.write_text(json.dumps(self.blocks, indent=2))

    def register(self, raw: bytes, note="", name=""):
        core = {"index": len(self.blocks), "name": name, "note": note, "file_hash": sha256_bytes(raw),
                "prev_hash": self.blocks[-1]["block_hash"] if self.blocks else "GENESIS",
                "timestamp": dt.datetime.now(dt.timezone.utc).isoformat()}
        bh = _block_hash(core)
        self.blocks.append({**core, "block_hash": bh, "signature": _sign(bh)})
        self.save()

    def is_registered(self, raw: bytes) -> bool:
        h = sha256_bytes(raw)
        return any(b["file_hash"] == h for b in self.blocks)

    def chain_intact(self) -> bool:
        for i, b in enumerate(self.blocks):
            core = {k: v for k, v in b.items() if k not in ("block_hash", "signature")}
            if _block_hash(core) != b["block_hash"]:
                return False
            if b["prev_hash"] != (self.blocks[i - 1]["block_hash"] if i else "GENESIS"):
                return False
            if not hmac.compare_digest(_sign(b["block_hash"]), b["signature"]):
                return False
        return True
