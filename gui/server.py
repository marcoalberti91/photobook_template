#!/usr/bin/env python3
"""
Photobook Builder — server senza dipendenze esterne (stdlib Python 3).

Avvio:
    python gui/server.py          (dalla root del progetto)
    python server.py              (dalla cartella gui/)
    → apri http://localhost:5555
"""
import json, mimetypes, re, subprocess, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

# ── Trova la root del progetto ────────────────────────────────────────────
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

# ── Costanti regex ────────────────────────────────────────────────────────
_CLEARPAGE_RE = re.compile(r'\n[ \t]*\\clearpage[ \t]*\n')
_RE_ACTIVE    = re.compile(r'^\s*\\include\{sections/([^}]+)\}',  re.MULTILINE)
_RE_INACTIVE  = re.compile(r'^\s*%\s*\\include\{sections/([^}]+)\}', re.MULTILINE)
_RE_ANY_INC   = re.compile(r'^\s*%?\s*\\include\{sections/[^}]+\}', re.MULTILINE)
_RE_END_DOC   = re.compile(r'^\s*\\end\{document\}', re.MULTILINE)
_IMAGE_EXTS   = {'.jpg', '.jpeg', '.png', '.webp', '.tiff'}
_LABEL_RE     = re.compile(r'^\\label\{pb-[^}]+\}[ \t]*\n?', re.MULTILINE)


# ── Helpers per la gestione di pagine nei file .tex ───────────────────────
def split_pages(content: str):
    """Restituisce (header, [page_blocks]) separati da \\clearpage."""
    parts = _CLEARPAGE_RE.split(content)
    return parts[0], parts[1:]


def join_pages(header: str, pages: list) -> str:
    if not pages:
        return header
    return "\n\\clearpage\n".join([header] + pages)


def extract_command(block: str) -> str | None:
    for line in block.strip().splitlines():
        line = line.strip()
        if not line or line.startswith('\\label{pb-'):
            continue
        m = re.match(r'\\([a-zA-Z]+)', line)
        if m:
            return m.group(1)
    return None


def extract_images(block: str) -> list:
    candidates = re.findall(r'\{([^}]+)\}', block)
    return [c.strip() for c in candidates
            if c.strip() and Path(c.strip()).suffix.lower() in _IMAGE_EXTS]


# ── Helpers per main.tex ──────────────────────────────────────────────────
def read_main()  -> str:  return (ROOT / "main.tex").read_text(encoding="utf-8")
def write_main(c: str):   (ROOT / "main.tex").write_text(c, encoding="utf-8")
def active_slugs(c: str) -> set:
    return {m.group(1) for m in _RE_ACTIVE.finditer(c)}


class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print(f"  {self.command:6} {self.path.split('?')[0]}")

    # ── Router ────────────────────────────────────────────────────────
    def do_GET(self):
        p = urlparse(self.path)
        q = parse_qs(p.query)
        path = p.path

        if   path == "/":          self._file(GUI / "photobook-builder.html", "text/html")
        elif path == "/pdf":       self._pdf()
        elif path == "/images":    self._json(self._list_images())
        elif path == "/sections":  self._json(self._list_sections())
        elif path == "/page-map":  self._json(self._page_map())
        elif path == "/header":
            self._json(self._get_header(unquote(q.get("section", [""])[0])))
        elif path == "/pages":
            self._json(self._list_pages(unquote(q.get("section", [""])[0])))
        elif path == "/image":
            self._image(unquote(q.get("path", [""])[0]))
        else:
            self._send(404, "text/plain", b"Not found")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)
        try:   data = json.loads(body) if body else {}
        except json.JSONDecodeError: data = {}

        routes = {
            "/insert":         lambda: self._insert(data),
            "/compile":        lambda: self._compile(),
            "/new-chapter":    lambda: self._new_chapter(data),
            "/toggle-section": lambda: self._toggle_section(data),
            "/update-page":    lambda: self._update_page(data),
            "/delete-page":    lambda: self._delete_page(data),
            "/update-header":  lambda: self._update_header(data),
        }
        fn = routes.get(self.path)
        if fn:
            self._json(fn())
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
        if not rel: self._send(400, "text/plain", b"Missing path"); return
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
        if not path.exists(): self._send(404, "text/plain", b"Not found"); return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _list_images(self):
        imgs_dir = ROOT / "images"
        if not imgs_dir.exists(): return []
        result, seen = [], set()
        for f in sorted(imgs_dir.rglob("*")):
            if f.is_file() and f.suffix.lower() in _IMAGE_EXTS:
                rel = str(f.relative_to(ROOT)).replace("\\", "/")
                if rel not in seen:
                    seen.add(rel)
                    result.append({"path": rel, "name": f.name})
        return result

    def _list_sections(self):
        d = ROOT / "sections"
        if not d.exists(): return []
        content = read_main()
        active  = active_slugs(content)
        return [{"name": f.name, "active": f.stem in active}
                for f in sorted(d.glob("*.tex"))]

    def _list_pages(self, section_name: str) -> list:
        """Return [{index, command, images}] for pages added via the builder."""
        if not section_name: return []
        path = ROOT / "sections" / Path(section_name).name
        if not path.exists(): return []
        _, pages = split_pages(path.read_text(encoding="utf-8"))
        result = []
        for i, block in enumerate(pages):
            block = block.strip()
            result.append({
                "index":   i,
                "command": extract_command(block),
                "images":  extract_images(block),
            })
        return result

    # ── POST handlers ─────────────────────────────────────────────────
    def _insert(self, data) -> dict:
        section = data.get("section", "").strip()
        latex   = data.get("latex",   "").strip()
        if not section or not latex:
            return {"ok": False, "error": "Campi mancanti"}
        path = ROOT / "sections" / Path(section).name
        if not path.exists():
            return {"ok": False, "error": f"File non trovato: {section}"}
        content = path.read_text(encoding="utf-8")
        _, existing = split_pages(content)
        slug  = Path(section).stem
        label = f"\\label{{pb-{slug}-{len(existing)}}}"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(f"\n\\clearpage\n{label}\n{latex}\n")
        return {"ok": True}

    def _update_page(self, data) -> dict:
        section = data.get("section", "").strip()
        index   = data.get("index")
        latex   = data.get("latex",   "").strip()
        if not section or not latex or index is None:
            return {"ok": False, "error": "Campi mancanti"}
        path = ROOT / "sections" / Path(section).name
        if not path.exists():
            return {"ok": False, "error": f"File non trovato: {section}"}
        content = path.read_text(encoding="utf-8")
        header, pages = split_pages(content)
        if not (0 <= index < len(pages)):
            return {"ok": False, "error": f"Indice pagina non valido: {index}"}
        slug  = Path(section).stem
        label = f"\\label{{pb-{slug}-{index}}}"
        pages[index] = f"{label}\n{latex}"
        path.write_text(join_pages(header, pages), encoding="utf-8")
        return {"ok": True}

    def _delete_page(self, data) -> dict:
        section = data.get("section", "").strip()
        index   = data.get("index")
        if not section or index is None:
            return {"ok": False, "error": "Campi mancanti"}
        path = ROOT / "sections" / Path(section).name
        if not path.exists():
            return {"ok": False, "error": f"File non trovato: {section}"}
        content = path.read_text(encoding="utf-8")
        header, pages = split_pages(content)
        if not (0 <= index < len(pages)):
            return {"ok": False, "error": f"Indice pagina non valido: {index}"}
        del pages[index]
        # Re-label remaining pages so PDF page-map stays consistent
        slug = Path(section).stem
        pages = [f"\\label{{pb-{slug}-{i}}}\n{_LABEL_RE.sub('', p).strip()}"
                 for i, p in enumerate(pages)]
        path.write_text(join_pages(header, pages), encoding="utf-8")
        return {"ok": True}

    def _get_header(self, section_name: str) -> dict:
        if not section_name:
            return {"ok": False, "error": "Section mancante"}
        path = ROOT / "sections" / Path(section_name).name
        if not path.exists():
            return {"ok": False, "error": f"File non trovato: {section_name}"}
        header, _ = split_pages(path.read_text(encoding="utf-8"))

        r = {"ok": True,
             "day": "", "title": "", "date": "", "city": "", "country": "",
             "flag_image": "", "superficie": "", "popolazione": "", "description": "",
             "portrait_images": [], "text_date": "", "text": ""}

        m = re.search(r'\\textbf\{Day\s+([^}]+)\}', header)
        if m: r["day"] = m.group(1).strip()

        # title: token between first and second \textbar\
        m = re.search(r'\\textbf\{Day[^}]+\}\s*\\textbar\\\s+(.*?)\s*\\textbar\\', header, re.DOTALL)
        if m: r["title"] = m.group(1).strip()

        # date: DD Month YYYY anywhere in the title line
        m = re.search(r'\b(\d{1,2}\s+\w+\s+\d{4})\b', header)
        if m: r["date"] = m.group(1).strip()

        # city, country: after last \textbar\ → \textbf{CITY}, COUNTRY}
        m = re.search(r'\\textbar\\\s+\\textbf\{([^}]+)\},\s*([^}\n]+)', header)
        if m:
            r["city"]    = m.group(1).strip()
            r["country"] = m.group(2).strip()

        # flag image: first includegraphics inside a minipage
        m = re.search(
            r'\\begin\{minipage\}.*?\\includegraphics\[width=\\textwidth\]\{([^}]+)\}',
            header, re.DOTALL)
        if m: r["flag_image"] = m.group(1).strip()

        m = re.search(r'\\textbf\{Superficie\}:\s*([^\\\n]+)', header)
        if m: r["superficie"] = m.group(1).strip()

        m = re.search(r'\\textbf\{Popolazione\}:\s*([^\\\n]+)', header)
        if m: r["popolazione"] = m.group(1).strip()

        m = re.search(r'\\textit\{([^}]+)\}', header)
        if m: r["description"] = m.group(1).strip()

        r["portrait_images"] = re.findall(r'\\portraitLargeMargin\{([^}]+)\}', header)

        # text block: after \noindent DATE \newline \newline
        m = re.search(r'\\noindent\s+(.*?)\\newline\s*\\newline\s*\n(.*?)$', header, re.DOTALL)
        if m:
            r["text_date"] = m.group(1).strip()
            r["text"]      = m.group(2).strip()

        return r

    def _update_header(self, data) -> dict:
        section = data.get("section", "").strip()
        if not section:
            return {"ok": False, "error": "Section mancante"}
        path = ROOT / "sections" / Path(section).name
        if not path.exists():
            return {"ok": False, "error": f"File non trovato: {section}"}

        day         = str(data.get("day",     "X")).strip()
        title       = data.get("title",       "Title").strip()
        date        = data.get("date",        "01 January 2020").strip()
        city        = data.get("city",        "City").strip()
        country     = data.get("country",     "Country").strip()
        flag_image  = data.get("flag_image",  "").strip()
        superficie  = data.get("superficie",  "").strip()
        popolazione = data.get("popolazione", "").strip()
        description = data.get("description", "").strip()
        portraits   = [p.strip() for p in data.get("portrait_images", []) if str(p).strip()]
        text_date   = (data.get("text_date", "") or date).strip()
        raw_text    = data.get("text", "").strip()

        hdr  = (f"\\begin{{center}}\n"
                f"    {{\\large \\textbf{{Day {day}}} \\textbar\\ {title} \\textbar\\"
                f" {date} \\textbar\\ \\textbf{{{city}}}, {country}}}\n"
                f"\\end{{center}}\n\n"
                f"\\noindent\\rule{{\\textwidth}}{{0.4pt}}\n")

        if flag_image:
            hdr += (f"\\begin{{figure}}[h!]\n"
                    f"    \\centering\n"
                    f"    \\begin{{minipage}}[h]{{0.48\\textwidth}}\n"
                    f"        \\centering\n"
                    f"        \\includegraphics[width=\\textwidth]{{{flag_image}}}\n"
                    f"    \\end{{minipage}}\n"
                    f"    \\hfill\n"
                    f"    \\begin{{minipage}}[h]{{0.48\\textwidth}}\n"
                    f"        \\raggedright\n"
                    f"        \\textbf{{Superficie}}: {superficie} \\\\\n"
                    f"        \\vspace{{0.3cm}}\n"
                    f"        \\textbf{{Popolazione}}: {popolazione} \\\\\n"
                    f"        \\vspace{{0.3cm}}\n"
                    f"        \\textit{{{description}}}\n"
                    f"    \\end{{minipage}}\n"
                    f"\\end{{figure}}\n\n")

        if portraits:
            hdr += "\n".join(f"\\portraitLargeMargin{{{p}}}" for p in portraits) + "\n\n"

        if raw_text:
            paras = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
            hdr  += f"\\noindent {text_date} \\newline \\newline\n" + "\n\n".join(paras) + "\n"

        content  = path.read_text(encoding="utf-8")
        _, pages = split_pages(content)
        path.write_text(join_pages(hdr, pages), encoding="utf-8")
        return {"ok": True}

    def _page_map(self) -> list:
        """Return [{section, page_index, pdf_page}] parsed from main.aux labels."""
        aux = ROOT / "main.aux"
        if not aux.exists():
            return []
        text = aux.read_text(encoding="utf-8", errors="ignore")
        result = []
        # \newlabel{pb-SLUG-IDX}{{SEC}{PAGE}...}
        for m in re.finditer(
            r'\\newlabel\{pb-(.+)-(\d+)\}\{\{[^}]*\}\{(\d+)\}', text
        ):
            slug = m.group(1)
            idx  = int(m.group(2))
            page = int(m.group(3))
            result.append({"section": slug + ".tex", "page_index": idx, "pdf_page": page})
        return result

    def _compile(self) -> dict:
        t0 = time.time()
        try:
            r = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                cwd=ROOT, capture_output=True, text=True, timeout=120)
            secs = round(time.time() - t0, 1)
            if r.returncode == 0:
                return {"ok": True, "seconds": secs}
            errors = [l for l in r.stdout.splitlines() if l.startswith("!")]
            return {"ok": False, "error": "\n".join(errors) or r.stdout[-600:], "seconds": secs}
        except FileNotFoundError:
            return {"ok": False, "error": "pdflatex non trovato — installa MacTeX: https://tug.org/mactex/"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "Timeout (>120 s)"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _new_chapter(self, data) -> dict:
        raw  = data.get("name", "").strip()
        if not raw: return {"ok": False, "error": "Nome vuoto"}
        slug = re.sub(r"[^a-zA-Z0-9_-]", "_", raw).strip("_")
        if not slug: return {"ok": False, "error": "Nome non valido"}
        filepath = ROOT / "sections" / f"{slug}.tex"
        if filepath.exists():
            return {"ok": False, "error": f"{slug}.tex esiste già"}
        template = (
            r"\begin{center}" + "\n"
            r"    {\large \textbf{Day X} \textbar\ Title \textbar\ 01 January 2020 \textbar\ \textbf{City}, Country}" + "\n"
            r"\end{center}" + "\n\n"
            r"\noindent\rule{\textwidth}{0.4pt}" + "\n"
        )
        filepath.write_text(template, encoding="utf-8")
        # Insert \include into main.tex after last existing \include
        content = read_main()
        lines   = content.splitlines(keepends=True)
        last_inc, end_doc = -1, -1
        for i, line in enumerate(lines):
            if _RE_ANY_INC.match(line):  last_inc = i
            if _RE_END_DOC.match(line):  end_doc  = i
        insert_after = last_inc if last_inc >= 0 else max(end_doc - 1, 0)
        lines.insert(insert_after + 1, f"\\include{{sections/{slug}}}\n")
        write_main("".join(lines))
        return {"ok": True, "name": f"{slug}.tex", "slug": slug}

    def _toggle_section(self, data) -> dict:
        section = data.get("section", "").strip()
        active  = bool(data.get("active", True))
        slug    = section.replace(".tex", "")
        if not slug: return {"ok": False, "error": "Section mancante"}
        content   = read_main()
        lines     = content.splitlines(keepends=True)
        new_lines = []
        found     = False
        pat_a = re.compile(r'^(\s*)\\include\{sections/' + re.escape(slug) + r'\}(.*\n?)')
        pat_i = re.compile(r'^(\s*)%\s*\\include\{sections/' + re.escape(slug) + r'\}(.*\n?)')
        for line in lines:
            ma, mi = pat_a.match(line), pat_i.match(line)
            if ma:
                found = True
                new_lines.append(line if active else f"{ma.group(1)}% \\include{{sections/{slug}}}{ma.group(2)}")
            elif mi:
                found = True
                new_lines.append(f"{mi.group(1)}\\include{{sections/{slug}}}{mi.group(2)}" if active else line)
            else:
                new_lines.append(line)
        if not found:
            return {"ok": False, "error": f"{slug} non trovato in main.tex"}
        write_main("".join(new_lines))
        return {"ok": True}

    # ── Low-level response helpers ─────────────────────────────────────
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
