#!/usr/bin/env python3
"""
Photobook Builder — server senza dipendenze esterne
Usa solo la libreria standard di Python 3.

Avvio:
    python gui/server.py          (dalla root del progetto)
    python server.py              (dalla cartella gui/)
    → apri http://localhost:5555
"""
import json, mimetypes, subprocess, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

# ── Trova la root del progetto (contiene main.tex) ───────────────────────
def find_root():
    for d in [Path.cwd(),
              Path(__file__).resolve().parent,
              Path(__file__).resolve().parent.parent]:
        if (d / "main.tex").exists():
            return d.resolve()
    raise SystemExit(
        "❌  main.tex non trovato.\n"
        "    Avvia server.py dalla root del progetto:\n"
        "      python gui/server.py"
    )

ROOT = find_root()
GUI  = Path(__file__).resolve().parent
print(f"\n  📁  Progetto : {ROOT}")
print(f"  🌐  Apri     : http://localhost:5555\n")


class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"  {self.command:6} {self.path.split('?')[0]}")

    # ── Router ────────────────────────────────────────────────────────
    def do_GET(self):
        p = urlparse(self.path)
        q = parse_qs(p.query)
        path = p.path

        if path == "/":
            self._file(GUI / "photobook-builder.html", "text/html")
        elif path == "/pdf":
            self._pdf()
        elif path == "/images":
            self._json(self._list_images())
        elif path == "/image":
            self._image(unquote(q.get("path", [""])[0]))
        elif path == "/sections":
            self._json(self._list_sections())
        else:
            self._send(404, "text/plain", b"Not found")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}

        if self.path == "/insert":
            self._json(self._insert(data))
        elif self.path == "/compile":
            self._json(self._compile())
        else:
            self._send(404, "text/plain", b"Not found")

    def do_OPTIONS(self):
        self._send(204, "text/plain", b"")

    # ── Handlers ──────────────────────────────────────────────────────
    def _pdf(self):
        p = ROOT / "main.pdf"
        if not p.exists():
            self._send(404, "text/plain", b"PDF non trovato. Compila prima.")
            return
        data = p.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store, no-cache")
        self.end_headers()
        self.wfile.write(data)

    def _image(self, rel):
        if not rel:
            self._send(400, "text/plain", b"Missing path"); return
        full = (ROOT / rel).resolve()
        if not str(full).startswith(str(ROOT)) or not full.exists():
            self._send(404, "text/plain", b"Not found"); return
        mime = mimetypes.guess_type(str(full))[0] or "application/octet-stream"
        data = full.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "max-age=3600")
        self.end_headers()
        self.wfile.write(data)

    def _file(self, path: Path, mime: str):
        if not path.exists():
            self._send(404, "text/plain", b"Not found"); return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _list_images(self):
        imgs_dir = ROOT / "images"
        if not imgs_dir.exists():
            return []
        result, seen = [], set()
        for f in sorted(imgs_dir.rglob("*")):
            if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".tiff"):
                rel = str(f.relative_to(ROOT)).replace("\\", "/")
                if rel not in seen:
                    seen.add(rel)
                    result.append({"path": rel, "name": f.name})
        return result

    def _list_sections(self):
        d = ROOT / "sections"
        if not d.exists():
            return []
        return sorted(f.name for f in d.glob("*.tex"))

    def _insert(self, data):
        section = data.get("section", "").strip()
        latex   = data.get("latex",   "").strip()
        if not section or not latex:
            return {"ok": False, "error": "Campi mancanti"}
        path = ROOT / "sections" / Path(section).name
        if not path.exists():
            return {"ok": False, "error": f"File non trovato: {section}"}
        with path.open("a", encoding="utf-8") as fh:
            fh.write(f"\n{latex}\n")
        return {"ok": True}

    def _compile(self):
        t0 = time.time()
        try:
            r = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                cwd=ROOT, capture_output=True, text=True, timeout=120,
            )
            secs = round(time.time() - t0, 1)
            if r.returncode == 0:
                return {"ok": True, "seconds": secs}
            errors = [l for l in r.stdout.splitlines() if l.startswith("!")]
            return {"ok": False, "error": "\n".join(errors) or r.stdout[-600:], "seconds": secs}
        except FileNotFoundError:
            return {"ok": False, "error": "pdflatex non trovato — installa MacTeX: https://tug.org/mactex/"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "Timeout compilazione (>120 s)"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Helpers ───────────────────────────────────────────────────────
    def _send(self, code, mime, body: bytes):
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 5555), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server fermato.")
