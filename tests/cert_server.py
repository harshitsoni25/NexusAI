"""A deterministic, loopback-only test website for real-browser certification.

This is test-only infrastructure (Phase 10R-CV, closing CB-2): a standard-library
``ThreadingHTTPServer`` bound to ``127.0.0.1`` on an ephemeral port, serving fixed
pages that exercise the browser scenarios Nexus AI implements -- JavaScript
rendering, lazy loading, bounded infinite scroll, Load More, XHR/fetch/JSON and
GraphQL network activity, visual and DOM change, and slow/error paths. Nothing here
touches the public internet, uses external fonts/scripts/images, or embeds real
secrets; content is deterministic so a real browser produces stable results.

The server is driven by tests through :func:`serve`, which returns a running server
and its base URL and guarantees clean shutdown. No production code depends on this
module.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# --- Page bodies (deterministic; content injected by JS where the route requires it) ---

_STATIC = """<!doctype html><html><head><title>Static</title></head><body>
<ul id="items">
  <li class="item" data-id="1">Alpha</li>
  <li class="item" data-id="2">Beta</li>
  <li class="item" data-id="3">Gamma</li>
</ul></body></html>"""

# Target content is absent from the initial HTML and injected only by script.
_JAVASCRIPT = """<!doctype html><html><head><title>JS</title></head><body>
<div id="app">loading</div>
<script>
  var root = document.getElementById('app');
  root.innerHTML = '';
  var ul = document.createElement('ul'); ul.id = 'items';
  ['One','Two','Three'].forEach(function(name, i){
    var li = document.createElement('li');
    li.className = 'item'; li.setAttribute('data-id', String(i+1)); li.textContent = name;
    ul.appendChild(li);
  });
  root.appendChild(ul);
</script></body></html>"""

# Content appended as the page is scrolled, up to a fixed cap, then it stops.
_LAZY = """<!doctype html><html><head><title>Lazy</title></head><body>
<ul id="items"><li class="item" data-id="1">Seed</li></ul>
<div style="height:3000px"></div>
<script>
  var count = 1, cap = 5;
  function add(){ if(count>=cap) return;
    count++; var li=document.createElement('li');
    li.className='item'; li.setAttribute('data-id',String(count));
    li.textContent='Lazy '+count; document.getElementById('items').appendChild(li); }
  window.addEventListener('scroll', add);
</script></body></html>"""

# Grows in batches on scroll until a fixed total, then stops (finite "infinite" scroll).
_INFINITE = """<!doctype html><html><head><title>Infinite</title></head><body>
<ul id="items"></ul><div style="height:5000px"></div>
<script>
  var total = 0, cap = 9, batch = 3;
  function render(){ var ul=document.getElementById('items'); ul.innerHTML='';
    for(var i=1;i<=total;i++){ var li=document.createElement('li');
      li.className='item'; li.setAttribute('data-id',String(i));
      li.textContent='Row '+i; ul.appendChild(li);} }
  function grow(){ if(total>=cap) return; total=Math.min(cap,total+batch); render(); }
  grow(); window.addEventListener('scroll', grow);
</script></body></html>"""

# Adds a batch on each button click; the button disables when the cap is reached.
_LOAD_MORE = """<!doctype html><html><head><title>LoadMore</title></head><body>
<ul id="items"><li class="item" data-id="1">Item 1</li><li class="item" data-id="2">Item 2</li></ul>
<button id="more">Load more</button>
<script>
  var count = 2, cap = 6;
  document.getElementById('more').addEventListener('click', function(){
    for(var i=0;i<2 && count<cap;i++){ count++; var li=document.createElement('li');
      li.className='item'; li.setAttribute('data-id',String(count)); li.textContent='Item '+count;
      document.getElementById('items').appendChild(li); }
    if(count>=cap){ this.disabled = true; this.style.display='none'; }
  });
</script></body></html>"""

# Issues a fetch to /api-json and an XHR to /api-fetch, then renders the results.
_API_PAGE = """<!doctype html><html><head><title>API</title></head><body>
<ul id="items"></ul>
<script>
  fetch('/api-json').then(function(r){return r.json();}).then(function(d){
    d.records.forEach(function(rec){ var li=document.createElement('li');
      li.className='item'; li.setAttribute('data-id',String(rec.id)); li.textContent=rec.name;
      document.getElementById('items').appendChild(li); });
  });
  var x = new XMLHttpRequest(); x.open('GET','/api-fetch'); x.send();
  var g = new XMLHttpRequest(); g.open('POST','/graphql');
  g.setRequestHeader('Content-Type','application/json');
  g.send(JSON.stringify({query:'{ items { id } }'}));
</script></body></html>"""

_VISUAL_BASELINE = """<!doctype html><html><head><title>V</title>
<style>body{margin:0}#box{width:200px;height:200px;background:#3366cc}</style>
</head><body><div id="box"></div></body></html>"""

_VISUAL_CHANGED = """<!doctype html><html><head><title>V</title>
<style>body{margin:0}#box{width:200px;height:200px;background:#cc3333}</style>
</head><body><div id="box"></div></body></html>"""

_DOM_BASELINE = """<!doctype html><html><head><title>D</title></head><body>
<ul id="items"><li class="item" data-id="1">A</li><li class="item" data-id="2">B</li></ul>
</body></html>"""

_DOM_CHANGED = """<!doctype html><html><head><title>D</title></head><body>
<ul id="items"><li class="item" data-id="1">A</li><li class="item" data-id="2">B-modified</li>
<li class="item" data-id="3">C</li></ul></body></html>"""


class _Handler(BaseHTTPRequestHandler):
    """Routes fixed content; loopback only, no external dependencies."""

    # Silence the default stderr request logging so test output stays clean.
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return

    def _send(self, body: bytes, *, status: int = 200, content_type: str = "text/html") -> None:
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, markup: str, *, status: int = 200) -> None:
        self._send(markup.encode("utf-8"), status=status, content_type="text/html")

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        routes = {
            "/": _STATIC,
            "/static": _STATIC,
            "/javascript": _JAVASCRIPT,
            "/lazy": _LAZY,
            "/infinite-scroll": _INFINITE,
            "/load-more": _LOAD_MORE,
            "/api-page": _API_PAGE,
            "/visual/baseline": _VISUAL_BASELINE,
            "/visual/changed": _VISUAL_CHANGED,
            "/dom/baseline": _DOM_BASELINE,
            "/dom/changed": _DOM_CHANGED,
        }
        if path in routes:
            self._html(routes[path])
        elif path == "/api-json":
            self._send(
                json.dumps(
                    {"records": [{"id": 1, "name": "Api One"}, {"id": 2, "name": "Api Two"}]}
                ).encode(),
                content_type="application/json",
            )
        elif path == "/api-fetch":
            self._send(json.dumps({"ok": True}).encode(), content_type="application/json")
        elif path == "/slow":
            time.sleep(2.0)  # deterministic delay for timeout/readiness testing
            self._html("<html><body><div id='late'>late</div></body></html>")
        elif path == "/error":
            self._html("<html><body>error</body></html>", status=500)
        else:
            self._html("<html><body>not found</body></html>", status=404)

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/graphql":
            length = int(self.headers.get("Content-Length", "0"))
            self.rfile.read(length)  # consume body; no auth, no introspection
            self._send(
                json.dumps({"data": {"items": [{"id": 1}, {"id": 2}]}}).encode(),
                content_type="application/json",
            )
        else:
            self._html("<html><body>not found</body></html>", status=404)


@contextmanager
def serve() -> Iterator[str]:
    """Run the certification server on a loopback ephemeral port, yielding its base URL.

    The server starts in a background thread and is shut down and joined on exit, so
    no orphan process or thread survives the test session.
    """
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host = str(server.server_address[0])
    port = int(server.server_address[1])
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
