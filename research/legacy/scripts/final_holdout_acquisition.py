"""Bounded, checksummed official archive retrieval with persistent request budgets."""
import json
from datetime import UTC, datetime

from acquire_usdm_universe import verify_payload
from audit_development_continuity import sha
from final_holdout_common import write
from reconcile_mark_gaps import ProbeClient
from recover_development_marks import Pace


class Archives:
    def __init__(self, root, requests, compressed, jobs):
        self.root, self.limits = root, (requests, compressed, jobs)
        self.state_path = root / "budget.json"
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {
            "requests": 0, "compressed_bytes": 0, "jobs": []}
        self.pace = Pace()

    def fetch(self, key, url):
        folder = self.root / key
        meta_path = folder / "source.json"
        filename = url.rsplit("/", 1)[1]
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            body, checksum = (folder / "archive.zip").read_bytes(), (folder / "checksum.txt").read_bytes()
            if meta["url"] != url or meta["sha256"] != sha(folder / "archive.zip"):
                raise ValueError("Archive source mismatch")
            verify_payload(body, checksum, filename, len(body))
            return body, meta
        if key not in self.state["jobs"]:
            if len(self.state["jobs"]) >= self.limits[2]:
                raise ValueError("Source-day/month job budget exceeded")
            self.state["jobs"].append(key)
            write(self.state_path, self.state)
        attempt = folder / datetime.now(UTC).strftime("attempt_%Y%m%dT%H%M%S%fZ")
        client = ProbeClient(attempt)
        payloads = []
        try:
            for name, target, limit in (("checksum", url+".CHECKSUM", 4096), ("archive", url, 2*1024**2)):
                if name == "archive":
                    limit = min(limit, self.limits[1]-self.state["compressed_bytes"])
                    if limit <= 0:
                        raise ValueError("Compressed byte budget exhausted")
                if self.state["requests"] >= self.limits[0]:
                    raise ValueError("HTTP request budget exceeded")
                self.state["requests"] += 1
                write(self.state_path, self.state)
                self.pace.wait()
                payload = client.get(name, target, limit)
                if name == "archive":
                    self.state["compressed_bytes"] += len(payload)
                    write(self.state_path, self.state)
                    if self.state["compressed_bytes"] > self.limits[1]:
                        raise ValueError("Compressed byte budget exceeded")
                payloads.append(payload)
        finally:
            write(attempt / "manifest.json", client.manifest)
        checksum, body = payloads
        verify_payload(body, checksum, filename, len(body))
        (folder / "archive.zip").write_bytes(body)
        (folder / "checksum.txt").write_bytes(checksum)
        meta = {"url": url, "sha256": sha(folder / "archive.zip"), "bytes": len(body),
                "retrieved_at": client.manifest[-1]["retrieved_at"]}
        write(meta_path, meta)
        return body, meta
