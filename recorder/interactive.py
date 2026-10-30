#!/usr/bin/env python3
"""Records the click-through demos: drives a SUSE AI Factory with NVIDIA installation while
`interactive-demo capture` turns every click into a step.

    python3 recorder/interactive.py chrome            # the recording Chrome (headless, port 9336), logged in everywhere
    python3 recorder/interactive.py record <slug> [segment ...]
    node scripts/merge-segments.mjs <slug>            # then: the demo, following stories/<slug>.json

A demo is recorded in segments (flow, device, rancher, security, observability), one capture session
each, into recordings/<slug>/<segment>/. The browser helpers and the per-demo click sequences come from
the aif-dev repository's docs/videos (AIF_DEV, default ~/Documents/innovation/aif-dev), which also
made the demo videos.

Needs the tunnels to the installation:
    ssh -f -N -L 8900:127.0.0.1:8900 -L 8443:169.254.100.1:8443 -L 3000:127.0.0.1:3000 \
        -L 30880:127.0.0.1:30880 -L 30843:127.0.0.1:30843 spark
"""
import contextlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AIF_DEV = Path(os.environ.get("AIF_DEV", Path.home() / "Documents" / "innovation" / "aif-dev"))
sys.path.insert(0, str(AIF_DEV / "docs" / "videos"))

import guided  # noqa: E402
import record  # noqa: E402

PORT = 9336
PROFILE = Path.home() / ".aif-video" / "chrome-saif"
CDP = f"http://127.0.0.1:{PORT}"
CLI = [str(ROOT / "node_modules" / ".bin" / "interactive-demo")]


def credentials(path):
    return json.load(urllib.request.urlopen(f"{record.DEVICE}/api/v1/{path}", timeout=30))


# ---------------------------------------------------------------------------- browser ---

def chrome():
    """The recording Chrome: headless, its own profile, the device's names mapped to the tunnels."""
    try:
        urllib.request.urlopen(f"{CDP}/json/version", timeout=2)
    except Exception:
        subprocess.Popen([record.CHROME, "--headless=new", f"--user-data-dir={PROFILE}", f"--remote-debugging-port={PORT}",
                          "--remote-allow-origins=*", "--ignore-certificate-errors", "--no-first-run", "--hide-scrollbars",
                          "--host-resolver-rules=MAP rancher.aif.internal 127.0.0.1, MAP spark-8528.local 127.0.0.1",
                          "--window-size=1440,900", "--force-device-scale-factor=2", "about:blank"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        for _ in range(50):
            try:
                urllib.request.urlopen(f"{CDP}/json/version", timeout=2)
                break
            except Exception:
                time.sleep(0.2)
    login_all()


class Tab(record.Browser):
    """A tab of the recording Chrome: a new one (target=None), or the one a capture session records."""

    def __init__(self, target=None):
        self.proc, self.attached = None, PORT
        if target is None:
            req = urllib.request.Request(f"{CDP}/json/new?about:blank", method="PUT")
            page = json.load(urllib.request.urlopen(req))
        else:
            page = next(t for t in json.load(urllib.request.urlopen(f"{CDP}/json")) if t["id"] == target)
        self.target = page["id"]
        self._connect(page)

    def call(self, method, timeout=60, **params):
        if method == "Emulation.setDeviceMetricsOverride":  # the capture owns the viewport (1440 x 900)
            return {}
        return super().call(method, timeout=timeout, **params)


def type_login(b, user_js, password_js, user, password, submit_js):
    b.wait(f"!!({password_js})", timeout=60)
    b.type_into(user_js, user)
    b.type_into(password_js, password)
    b.js(submit_js)
    time.sleep(6)


def login_all():
    b = Tab()
    try:
        r = credentials("rancher")
        b.go(record.RANCHER + "/dashboard/auth/login", settle=6)
        if b.js("!!document.querySelector('input[type=password]')"):
            type_login(b, "document.querySelector('[data-testid=local-login-username]')",
                       "document.querySelector('input[type=password]')", r["username"], r["password"],
                       "document.querySelector('#submit, button[type=submit]').click()")
        g = credentials("gitea")
        b.go(record.GITEA + "/user/login", settle=3)
        if b.js("!!document.querySelector('input[type=password]')"):
            type_login(b, "document.querySelector('#user_name')", "document.querySelector('#password')",
                       g["username"], g["password"], "document.querySelector('form.ui.form button.primary, form button').click()")
        s = credentials("security")
        b.go(record.SECURITY + "/", settle=6)
        if b.js("!!document.querySelector('input[type=password]')"):
            type_login(b, "document.querySelector('input[formcontrolname=username], input[name=username], input[type=text]')",
                       "document.querySelector('input[type=password]')", s["username"], s["password"],
                       "[...document.querySelectorAll('button')].find(x => /login/i.test(x.textContent))?.click()")
        o = credentials("observability")
        b.go(record.OBSERVABILITY + "/", settle=6)
        if b.js("!!document.querySelector('input[type=password]')"):
            type_login(b, "document.querySelector('input[name=username], #username, input[type=text]')",
                       "document.querySelector('input[type=password]')", o["username"], o["password"],
                       "document.querySelector('button[type=submit], input[type=submit]').click()")
        b.go(record.RANCHER + "/dashboard/c/local/suseai/overview", settle=6)
        print("logged in:", "rancher" if "auth/login" not in b.js("location.href") else "RANCHER LOGIN FAILED", flush=True)
    finally:
        b.close()


# ---------------------------------------------------------------------------- capture ---

def cli(*args):
    out = subprocess.run(CLI + list(args), cwd=ROOT, capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"interactive-demo {' '.join(args)}: {out.stderr or out.stdout}")
    return json.loads(out.stdout) if out.stdout.strip().startswith("{") else out.stdout


# The hardware and the machine's name never show: blurred wherever they appear on a page.
BLUR = r"""(() => {
  if (window.__saifBlur) return; window.__saifBlur = true;
  const RE = /(on a |an? )?(NVIDIA )?DGX Spark|spark-8528(\.local)?/g;
  const wrap = (node) => {
    const text = node.nodeValue; RE.lastIndex = 0;
    if (!RE.test(text) || node.parentElement?.closest('[data-saif-blur], script, style, textarea')) return;
    const frag = document.createDocumentFragment(); let last = 0; RE.lastIndex = 0; let m;
    while ((m = RE.exec(text))) {
      frag.append(text.slice(last, m.index));
      const s = document.createElement('span'); s.dataset.saifBlur = '1';
      s.style.filter = 'blur(5px)'; s.textContent = m[0]; frag.append(s); last = m.index + m[0].length;
    }
    frag.append(text.slice(last)); node.replaceWith(frag);
  };
  const scan = (root) => {
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT); const nodes = [];
    while (w.nextNode()) nodes.push(w.currentNode); nodes.forEach(wrap);
    root.querySelectorAll?.('input, textarea').forEach((i) => { RE.lastIndex = 0; if (RE.test(i.value)) i.style.filter = 'blur(5px)'; });
  };
  const start = () => { scan(document.body); new MutationObserver((ms) => ms.forEach((m) => {
    m.addedNodes.forEach((n) => n.nodeType === 3 ? wrap(n) : n.nodeType === 1 && scan(n));
    if (m.type === 'characterData') wrap(m.target); })).observe(document.body, { childList: true, subtree: true, characterData: true }); };
  document.body ? start() : document.addEventListener('DOMContentLoaded', start);
})()"""


@contextlib.contextmanager
def segment(slug, name, url):
    """One capture session: every click on the yielded tab becomes a step of recordings/<slug>/<name>/."""
    out = ROOT / "recordings" / slug / name
    shutil.rmtree(out, ignore_errors=True)
    started = cli("capture", "start", url, "--name", f"{slug}-{name}", "--connect-to-browser", CDP,
                  "--no-video", "--compress-images")
    session = started["session"]["id"]
    b = Tab(started["tab"]["targetId"])
    b.call("Page.addScriptToEvaluateOnNewDocument", source=BLUR)
    b.js(BLUR)
    time.sleep(3)
    try:
        yield b
        time.sleep(2)
        stopped = cli("capture", "stop", "--session", session, "--out", str(out))
        print(f"{slug}/{name}: {stopped['output']['stepCount']} steps", flush=True)
    except BaseException:
        cli("capture", "cancel", "--session", session)
        raise
    finally:
        with contextlib.suppress(Exception):
            b.ws.close()


def shot(b, target_js, wait_js=None, timeout=900):
    """A step showing the page as it is now: a click on target_js, which does nothing on the page,
    once wait_js is true. The step's hotspot points at target_js."""
    if wait_js:
        b.wait(wait_js, timeout=timeout, every=1)
    time.sleep(1.5)
    b.wait(f"(() => {{ const el = {target_js}; if (!el) return false; el.click(); return true }})()", timeout=60, every=0.5)
    time.sleep(2.5)


def text_el(text, selector="body *"):
    """JS for the innermost visible element whose text includes text."""
    return (f"[...document.querySelectorAll({json.dumps(selector)})].filter(e => e.offsetParent !== null && "
            f"e.textContent.includes({json.dumps(text)})).at(-1)")


if __name__ == "__main__":
    cmd = sys.argv[1:2]
    if cmd == ["chrome"]:
        chrome()
    elif cmd == ["record"]:
        import demos_interactive
        demos_interactive.run(sys.argv[2], sys.argv[3:])
    else:
        sys.exit(__doc__)
