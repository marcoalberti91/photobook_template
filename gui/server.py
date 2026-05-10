#!/usr/bin/env python3
"""
Photobook Builder — server senza dipendenze esterne
Usa solo la libreria standard di Python 3.

Avvio:
    python gui/server.py          (dalla root del progetto)
    python server.py              (dalla cartella gui/)
    → apri http://localhost:5555
"""
import json, mimetypes, re, subprocess, time
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

# ── Pattern per \include{sections/SLUG} in main.tex ─────────────────────
_RE_ACTIVE   = re.compile(r'^(\s*)\\include\{sections/([^}]+)\}(.*)', re.MULTILINE)
_RE_INACTIVE = re.compile(r'^(\s*)%\s*\\include\{sections/([^}]+)\}(.*)', re.MULTILINE)
_RE_ANY      = re.compile(r'^\s*%?\s*\\include\{sections/[^}]+\}', re.MULTILINE)
_RE_END_DOC  = re.compile(r'^\s*\\end\{document\}', re.MULTILINE)


def _read_main():
    return (ROOT / "main.tex").read_text(encoding="utf-8")

def _write_main(content: str):
    (ROOT / "main.tex").write_text(content, encoding="utf-8")

def _active_slugs(content: str) -> set:
    return {m.group(2) for m in _RE_ACTIVE.finditer(content)}


class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"  {self.command:6} {self.path.split('?')[0]}")

    # ── Router ────────────────────────────────────────────────────────
    def do_GET(self):
        parsed = urlparse(self.path)
        q      = parse_qs(parsed.query)
        path   = parsed.path

        routes = {
            "/":         lambda: self._file(GUI / "photobook-builder.html", "text/html"),
            "/pdf":      self._pdf,
            "/images":   lambda: self._json(self._list_images()),
            "/sections": lambda: self._json(self._list_sections()),
        }
        if path in routes:
            routes[path]()
        elif path == "/image":
            self._image(unquote(q.get("path", [""])[0]))
        else:
            self._send(404, "text/plain", b"Not found")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}

        routes = {
            "/insert":         lambda: self._json(self._insert(data)),
            "/compile":        lambda: self._json(self._compile()),
            "/new-chapter":    lambda: self._json(self._new_chapter(data)),
            "/toggle-section": lambda: self._json(self._toggle_section(data)),
        }
        if self.path in routes:
            routes[self.path]()
        else:
            self._send(404, "text/plain", b"Not found")

    def do_OPTIONS(self):
        self._send(204, "text/plain", b"")

    # ── GET handlers ──────────────────────────────────────────────────
    def _pdf(self):
        p = ROOT / "main.pdf"
        if not p.exists():
            self._send(404, "text/plain", b"PDF non trovato. Compila prima."); return
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
        """Return [{name, active}] — active = not commented out in main.tex."""
        d = ROOT / "sections"
        if not d.exists():
            return []
        content = _read_main()
        active  = _active_slugs(content)
        return [
            {"name": f.name, "active": f.stem in active}
            for f in sorted(d.glob("*.tex"))
        ]

    # ── POST handlers ─────────────────────────────────────────────────
    def _insert(self, data):
        """Append a LaTeX layout command to a section file, preceded by \clearpage."""
        section = data.get("section", "").strip()
        latex   = data.get("latex",   "").strip()
        if not section or not latex:
            return {"ok": False, "error": "Campi mancanti"}
        path = ROOT / "sections" / Path(section).name
        if not path.exists():
            return {"ok": False, "error": f"File non trovato: {section}"}
        with path.open("a", encoding="utf-8") as fh:
            fh.write(f"\n\\clearpage\n{latex}\n")
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

    def _new_chapter(self, data):
        """Create a new section .tex file and register it in main.tex."""
        raw = data.get("name", "").strip()
        if not raw:
            return {"ok": False, "error": "Nome vuoto"}

        # Sanitise: keep only alphanumeric, hyphens, underscores
        slug = re.sub(r"[^a-zA-Z0-9_-]", "_", raw).strip("_")
        if not slug:
            return {"ok": False, "error": "Nome non valido (usa solo lettere, numeri, - _)"}

        filepath = ROOT / "sections" / f"{slug}.tex"
        if filepath.exists():
            return {"ok": False, "error": f"Il file {slug}.tex esiste già"}

        # Write section file with header template
        template = (
            r"\begin{center}" + "\n"
            r"    {\large \textbf{Day X} \textbar\ Title \textbar\ 01 January 2020 \textbar\ \textbf{City}, Country}" + "\n"
            r"\end{center}" + "\n\n"
            r"\noindent\rule{\textwidth}{0.4pt}" + "\n"
        )
        filepath.write_text(template, encoding="utf-8")

        # Insert \include{sections/SLUG} into main.tex
        content = _read_main()
        lines   = content.splitlines(keepends=True)

        # Find insertion point: after last \include{sections/...} line
        last_include = -1
        end_doc      = -1
        for i, line in enumerate(lines):
            if _RE_ANY.match(line):
                last_include = i
            if _RE_END_DOC.match(line):
                end_doc = i

        insert_after = last_include if last_include >= 0 else max(end_doc - 1, 0)
        lines.insert(insert_after + 1, f"\\include{{sections/{slug}}}\n")
        _write_main("".join(lines))

        return {"ok": True, "name": f"{slug}.tex", "slug": slug}

    def _toggle_section(self, data):
        """Comment or uncomment a \\include{sections/SLUG} line in main.tex."""
        section = data.get("section", "").strip()   # e.g. "day1.tex"
        active  = bool(data.get("active", True))
        slug    = section.replace(".tex", "")
        if not slug:
            return {"ok": False, "error": "Section mancante"}

        content = _read_main()
        lines   = content.splitlines(keepends=True)
        found   = False
        new_lines = []
        for line in lines:
            ma = re.match(r'^(\s*)\\include\{sections/' + re.escape(slug) + r'\}(.*\n?)', line)
            mi = re.match(r'^(\s*)%\s*\\include\{sections/' + re.escape(slug) + r'\}(.*\n?)', line)
            if ma:
                found = True
                if active:
                    new_lines.append(line)
                else:
                    new_lines.append(f"{ma.group(1)}% \\include{{sections/{slug}}}{ma.group(2)}")
            elif mi:
                found = True
                if active:
                    new_lines.append(f"{mi.group(1)}\\include{{sections/{slug}}}{mi.group(2)}")
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        if not found:
            return {"ok": False, "error": f"{slug} non trovato in main.tex"}

        _write_main("".join(new_lines))
        return {"ok": True}

    # ── Helpers ───────────────────────────────────────────────────────
    def _send(self, code, mime, body: bytes):
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj):
        body = json.dumps(obj, ensure_ascii=False).encode()
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
