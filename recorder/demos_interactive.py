"""The click paths of each demo, segment by segment. Every click is a step of the demo; shot() adds a
step where the page has something to show but nothing needs clicking.

Every demo tells the same story (user, 2026-10-30):
  flow           the architecture: the use case's Blueprint in the Studio
  saif           SUSE AI Factory with NVIDIA deploys the Blueprint (its Blueprints page, the install wizard)
  fleet          Fleet rolls it out (Continuous Delivery: the Blueprint's bundles)
  device         the demo's own UI, step by step, the whole window
  rancher        from SUSE AI Factory with NVIDIA into Rancher: the workload, its namespace, its pods
  security       SUSE Security, where the use case needs it
  observability  SUSE Observability: the Blueprint's workload as it is right now
"""
import json
import subprocess
import threading
import time
import urllib.request

import demos
import guided
import platform_videos as pv
import record

from interactive import ROOT, Tab, segment, shot, text_el

# Each demo's Blueprint: its name and version in SUSE AI Factory with NVIDIA, and how its tile is titled.
BLUEPRINT = {
    "manufacturing": ("factory-operations-visual-inspection", "0.4.0", "Factory Operations & Visual Inspection"),
    "finance": ("fraud-detection-investigation", "0.3.0", "Fraud Detection & Investigation"),
    "telco": ("network-configuration-autonomous-operations", "0.3.0", "Network Configuration & Autonomous Operations"),
    "retail": ("conversational-shopping-assistant", "0.3.0", "Conversational Shopping Assistant"),
    "healthcare": ("ambient-clinical-documentation", "0.3.1", "Ambient Clinical Documentation"),
    "secops": ("sovereign-agentic-secops", "0.3.0", "Sovereign Agentic SecOps"),
    "traffic": ("traffic-incident-management", "0.3.0", "Traffic Incident Management"),
    "sovereign": ("sovereign-casework", "0.1.3", "Public Sector – Sovereign Casework"),
    "developer-sandbox": ("developer-sandbox", "0.1.7", "Developer Sandbox"),
}
# The models each demo needs up (the others go to zero), as its page asks the device for them.
MODELS = dict(demos.MODELS, sovereign=["eurollm"])
# SUSE Observability names the Blueprints by their display names.
PLATFORM = dict(pv.PLATFORM, sovereign={"namespace": "ns-sovereign", "agent": "casework", "blueprint": "sovereign-casework",
                                        "name": "Sovereign Casework", "data": "the applicants' proposals"})


class NoMarks:
    def mark(self, name):
        pass


def node(kind):
    return f"document.querySelector('.fnode.k-{kind}')"


FLOW_READY = "document.querySelectorAll('.vue-flow__node').length > 3"


def studio_id(demo):
    name, version, _ = BLUEPRINT[demo]
    return f"{name}-{version.replace('.', '-')}"


def device_api(path, body):
    req = urllib.request.Request(f"{record.DEVICE}{path}", method="POST", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=300))


# --------------------------------------------------------------------------- segments ---

def record_flow(demo):
    """The architecture: the use case's Blueprint in the Studio, the agent, the model, what lies outside."""
    with segment(demo, "flow", f"{record.DEVICE}/studio/new?aif={studio_id(demo)}") as b:
        b.wait(FLOW_READY, timeout=60)
        time.sleep(4)
        shot(b, "document.querySelector('.vue-flow__pane')")  # the whole flow
        shot(b, node("agent"))           # the agent in its NVIDIA OpenShell sandbox
        shot(b, node("model"))           # the NVIDIA NIM it calls
        shot(b, node("external"))        # what the sandbox refuses


TILE = "[...document.querySelectorAll('.app-tile')].find(t => t.querySelector('.tile-title')?.textContent.trim() === {title})"


def record_saif(demo):
    """SUSE AI Factory with NVIDIA deploys the Blueprint: its tile, the install wizard, the workload."""
    name, version, title = BLUEPRINT[demo]
    guided.warm(MODELS.get(demo, ["nemotron-3-5-lightning"]))
    if demo == "secops":  # what the demo's page does before deploying: the Gitea bot, the estate, credentials
        device_api("/api/v1/demo/prepare", {"scenario": demo})
    tile = TILE.format(title=json.dumps(title))
    with segment(demo, "saif", f"{record.RANCHER}/dashboard/c/local/suseai/blueprints") as b:
        b.wait("!!document.querySelector('.app-tile')", timeout=90)
        b.js("(() => { const s = document.querySelector('select'); s.value = ''; s.dispatchEvent(new Event('change')) })()")
        b.wait(f"!!({tile})", timeout=30)
        b.js(f"({tile}).scrollIntoView({{block: 'center'}})")
        time.sleep(3)
        shot(b, f"({tile}).querySelector('.tile-title')")              # the Blueprint in the catalog
        b.js(f"[...({tile}).querySelectorAll('button')].find(x => x.textContent.trim() === 'Install').click()")
        b.wait("/Install Blueprint/.test(document.body.innerText)", timeout=60)
        time.sleep(4)
        shot(b, "document.querySelector('h1')")                         # the wizard: name and namespace
        for _ in range(3):                                              # basic information, cluster, configuration
            b.wait("!/Loading\\.\\.\\./.test(document.body.innerText)", timeout=90)
            time.sleep(2)
            b.click_text("Next", selector="button")
            time.sleep(4)
        review = b.js("document.body.innerText") or ""
        namespaces = [line.split("→")[1].split("(")[0].strip() for line in review.splitlines() if "→" in line]
        (ROOT / "recordings" / demo).mkdir(parents=True, exist_ok=True)
        (ROOT / "recordings" / demo / "namespaces.json").write_text(json.dumps(namespaces))
        b.click_text("Install", selector="button.role-primary, button")    # review, then install
        b.wait("/Scheduled for deployment/.test(document.body.innerText)", timeout=120)
        time.sleep(3)
        b.click_text("Done", selector="button")
        time.sleep(4)
        b.click_text("Workloads", selector="a")
        b.wait(f"/{name}/.test(document.body.innerText)", timeout=120)
        time.sleep(4)
        shot(b, f"[...document.querySelectorAll('tr')].find(t => t.textContent.includes('{name}'))")


def record_fleet(demo):
    """Fleet rolls the Blueprint out: its bundles in Continuous Delivery, one of them in detail."""
    name = BLUEPRINT[demo][0]
    rows = f"[...document.querySelectorAll('tbody tr')].filter(r => r.textContent.includes('{name}'))"
    with segment(demo, "fleet", f"{record.RANCHER}/dashboard/c/_/fleet/fleet.cattle.io.bundle") as b:
        b.wait(f"{rows}.length > 0 && {rows}.every(r => /Active/.test(r.textContent))", timeout=900, every=3)
        filt = "document.querySelector('input[placeholder=Filter], input.input-sm, .search input')"
        if b.js(f"!!({filt})"):
            b.type_into(filt, name)
            time.sleep(3)
        shot(b, f"{rows}[0].querySelector('a')")                        # the bundles; opens the first
        b.wait("/Bundle/.test(document.body.innerText) && !!document.querySelector('h1, .title')", timeout=60)
        time.sleep(5)
        shot(b, "document.querySelector('h1, .title')")                 # the bundle and what it deployed


def wait_ready(b, timeout=1200):
    b.wait("document.body.innerText.includes('SUSE AI Factory · ready') && /sandbox · Ready/.test(document.body.innerText)",
           timeout=timeout, every=3)


def record_device_guided(demo, steps=None):
    """The demo's page, already deployed: each step and its runs, with their results."""
    g = demos.GUIDED.get(demo)
    pv.clear_results(demo)
    with segment(demo, "device", f"{record.DEVICE}/demo/{demo}?step=1") as b:
        b.wait("!!document.querySelector('.step-link')", timeout=60)
        wait_ready(b)
        time.sleep(3)
        shot(b, text_el("SUSE AI Factory · ready"))                     # deployed through SUSE AI Factory with NVIDIA
        for title, runs in steps or g["runs"]:
            guided.step(b, NoMarks(), title)
            for label in runs:
                run_shown(b, label)


def run_shown(b, label, timeout=900):
    """Run one notebook section and wait for it; a step showing its last output."""
    guided.run(b, NoMarks(), label, dwell=1, timeout=timeout)
    block = guided.RUN_BLOCK.format(label=f'"{label}"')
    shot(b, f"(() => {{ const c = ({block})?.querySelectorAll('.cells > *'); return c?.[c.length - 1] }})()")


def namespace_of(demo):
    try:
        found = json.loads((ROOT / "recordings" / demo / "namespaces.json").read_text())
    except (OSError, ValueError):
        found = []
    own = [n for n in found if n not in ("openshell", "ns-agents", "ns-models")]
    return (own or found or [PLATFORM[demo]["namespace"]])[0]


def record_rancher(demo):
    """From SUSE AI Factory with NVIDIA into Rancher: the workload's details, its namespace, a deployment's pods."""
    name = BLUEPRINT[demo][0]
    ns = namespace_of(demo)
    with segment(demo, "rancher", f"{record.RANCHER}/dashboard/c/local/suseai/workloads") as b:
        b.wait(f"/{name}/.test(document.body.innerText)", timeout=90)
        time.sleep(3)
        b.click_text(name, selector="a")                                 # the workload, as SUSE AI Factory sees it
        b.wait("/Underlying Resources/.test(document.body.innerText)", timeout=60)
        time.sleep(2)
        b.js("[...document.querySelectorAll('*')].find(e => e.children.length === 0 && "
             "/Underlying Resources/.test(e.textContent))?.scrollIntoView({block: 'center'})")
        time.sleep(2)
        shot(b, text_el("Underlying Resources"))
        cluster = b.js("(() => { const a = [...document.querySelectorAll('a')].find(a => /\\/dashboard\\/c\\/c-[a-z0-9]+\\//"
                       ".test(a.getAttribute('href') || '')); return a ? a.getAttribute('href').split('/')[3] : '' })()")
        b.go(f"{record.RANCHER}/dashboard/c/{cluster or 'c-5nhkr'}/explorer/namespace/{ns}", settle=6)
        b.wait("/Resources/.test(document.body.innerText)", timeout=60)
        time.sleep(3)
        b.js("[...document.querySelectorAll('li.tab a')].find(e => /^Workloads/.test(e.textContent.trim())).click()")
        time.sleep(4)                                                   # the namespace in Rancher
        b.wait("!!document.querySelector('a[href*=\"apps.deployment/\"], a[href*=\"apps.statefulset/\"]')", timeout=60)
        b.js("document.querySelector('a[href*=\"apps.deployment/\"], a[href*=\"apps.statefulset/\"]').click()")
        time.sleep(7)
        shot(b, "document.querySelector('h1, .title')")                 # its pods, live


ROWS = ("[...document.querySelectorAll('.ag-center-cols-container .ag-row')].filter(r => "
        "r.textContent.includes('{ns}') && !/-[0-9a-f]{{6,}}/.test(r.querySelector('.ag-cell')?.textContent || ''))")


def record_security(demo, name, namespace, row=None):
    """SUSE Security: every container it scans, the use case's filtered, one container's vulnerabilities."""
    t = Tab()  # its session expires: log in first, outside the capture
    try:
        pv.security_login(t)
    finally:
        t.close()
    with segment(demo, name, record.SECURITY + "/#/workloads") as b:
        b.wait(f"!!({pv.FILTER})", timeout=90)
        time.sleep(4)
        shot(b, f"({pv.FILTER})")
        b.type_into(pv.FILTER, namespace)
        time.sleep(3)
        rows = ROWS.format(ns=namespace)
        pick = (f"[...document.querySelectorAll('.ag-center-cols-container .ag-row')].find(r => "
                f"r.querySelector('.ag-cell')?.textContent.trim() === '{row}')" if row else f"{rows}[0]")
        b.wait(f"!!({pick})", timeout=60)
        b.js(f"({pick}).querySelector('.ag-cell').click()")
        time.sleep(3)
        b.click_text("Vulnerabilities", selector="[role=tab]")
        time.sleep(6)
        shot(b, "document.querySelector('[role=tabpanel], .mat-mdc-tab-body-active')")


def record_observability(demo):
    """SUSE Observability: the Blueprint's workload as it is right now: the Blueprints, this one, its flow."""
    p = PLATFORM[demo]
    so = record.OBSERVABILITY
    with segment(demo, "observability", so + "/#/views/urn:stackpack:aif-demos:component-presentation:blueprint") as b:
        b.wait("/Showing \\d+ Blueprints/.test(document.body.innerText)", timeout=90)
        pv.settle(b, 3)
        # Its row, by the Blueprint's title (the list only draws the rows in view: else the list itself).
        shot(b, f"({text_el(BLUEPRINT[demo][2], 'a')}) || ({text_el('Showing')})")
        b.go(so + f"/#/components/urn:aif:blueprint:{p['blueprint']}", settle=2)
        b.wait("/Flow: what it is made of/.test(document.body.innerText)", timeout=60)
        pv.settle(b, 3)
        pv.click_link(b, "Flow: what it is made of")
        b.wait("!!document.querySelector('svg g, canvas') && /Topology/.test(document.body.innerText)", timeout=60)
        time.sleep(9)
        shot(b, "document.querySelector('svg g, canvas')")


# ----------------------------------------------------------------------------- demos ---

def finish_guided(demo):
    b = Tab()
    try:
        guided.finish(b, demo)
    finally:
        b.close()


def story(demo, parts, device, finish, security=()):
    """The segments in the story's order; parts: only those."""
    order = ["flow", "saif", "fleet", "device", "rancher", *[s[0] for s in security], "observability", "finish"]
    parts = parts or order
    for part in order:
        if part not in parts:
            continue
        if part == "flow":
            record_flow(demo)
        elif part == "saif":
            record_saif(demo)
        elif part == "fleet":
            record_fleet(demo)
        elif part == "device":
            device()
            time.sleep(30)  # the agent's traces and the Blueprint's health reach SUSE Observability
        elif part == "rancher":
            record_rancher(demo)
        elif part == "observability":
            record_observability(demo)
        elif part == "finish":
            finish()
        else:
            for name, namespace, *row in security:
                if part == name:
                    record_security(demo, name, namespace, *row)


SECOPS_STEPS = [("What SUSE Security sees", ["Read the findings"]), ("Triage", ["Triage the findings"]),
                ("The agent fixes it", ["Run the agent"]),
                ("Who merges? Not the agent", ["Let the agent try to merge and switch off scanning"])]
MERGE_WAIT = "Wait for the merge, the rollout and the rescan"


def secops_device():
    demo = "secops"
    record_device_guided(demo, SECOPS_STEPS)
    record_security(demo, "security-before", "ns-payments", "web")  # the storefront: 43 critical
    # The device waits for a person to merge the agent's pull request: started in a tab of its own, while the
    # engineer's side in Gitea is recorded.
    w = Tab()
    guided.open_demo(w, demo)
    guided.step(w, NoMarks(), "The engineer merges")
    waiting = threading.Thread(target=guided.run, args=(w, NoMarks(), MERGE_WAIT), kwargs={"timeout": 1800})
    waiting.start()
    time.sleep(8)
    try:
        record_gitea_merge(demo)
    finally:
        waiting.join()
        w.close()
    with segment(demo, "after", f"{record.DEVICE}/demo/{demo}") as b:
        b.wait("!!document.querySelector('.step-link')", timeout=60)
        time.sleep(3)
        guided.step(b, NoMarks(), "The engineer merges")
        block = guided.RUN_BLOCK.format(label=f'"{MERGE_WAIT}"')
        b.scroll_to(block, "start")
        time.sleep(2)
        shot(b, f"(() => {{ const c = ({block})?.querySelectorAll('.cells > *'); return c?.[c.length - 1] }})()")
        guided.step(b, NoMarks(), "The change record, and the boundary")
        run_shown(b, "Write the change record and try the internet")


def record_gitea_merge(demo):
    """The engineer's side in Gitea: the agent's issues, its pull request, the change, the merge."""
    t = Tab()  # log in first, outside the capture
    try:
        t.go(f"{record.GITEA}/user/login", settle=3)
        if t.js("!!document.querySelector('#password')"):
            g = json.load(urllib.request.urlopen(f"{record.DEVICE}/api/v1/gitea", timeout=30))
            t.type_into("document.querySelector('#user_name')", g["username"])
            t.type_into("document.querySelector('#password')", g["password"])
            t.js("document.querySelector('#password').form.submit()")
            time.sleep(4)
    finally:
        t.close()
    with segment(demo, "gitea", f"{record.GITEA}/{demos.ESTATE}/issues") as b:
        time.sleep(4)
        shot(b, "document.querySelector('#issue-list, .issue.list, .flex-list')")
        b.go(f"{record.GITEA}/{demos.ESTATE}/pulls", settle=4)
        b.js("document.querySelector('a.list-item-large-title, a.issue-title')?.click()")  # the newest open one
        time.sleep(5)
        pull = b.js("location.pathname")
        b.go(f"{record.GITEA}{pull}/files", settle=5)
        shot(b, "document.querySelector('.diff-file-box, .file-body')")
        b.go(f"{record.GITEA}{pull}", settle=4)
        b.js("document.querySelector('.merge-section, #pull-request-merge-form, .pull-merge-box')"
             "?.scrollIntoView({block: 'center'})")
        time.sleep(2)
        b.click_text("Create merge commit", selector="button")
        time.sleep(1.5)
        b.click_text("Create merge commit", selector="button[type=submit], .ui.form button")
        b.wait("/\\bmerged\\b/i.test(document.body.innerText.slice(0, 2000))", timeout=60)
        time.sleep(4)
        shot(b, "document.querySelector('.issue-title, h1')")


def traffic_device():
    demo = "traffic"
    subprocess.run(["ssh", "spark", "sudo -n rm -f /var/lib/aif-dev/demo-runs/traffic_traffic-operations_3.json"],
                   check=False)
    with segment(demo, "device", f"{record.DEVICE}/demo/traffic") as b:
        b.wait("document.querySelectorAll('.grid video').length >= 4", timeout=1200, every=3)
        b.wait("document.querySelectorAll('.grid .cam .ev').length >= 4", timeout=300, every=2)
        time.sleep(15)
        shot(b, "document.querySelector('.grid')")                      # the cameras, each with its verdict
        b.wait(f"!!({demos.ASKING})", timeout=900, every=2)
        b.js(f"({demos.ASKING}).scrollIntoView({{block: 'center'}})")
        time.sleep(4)
        shot(b, f"({demos.ASKING}).querySelector('.text, p')")          # the agent asks the operator
        b.js(f"({demos.ASKING}).querySelector('.opts button').click()")  # the operator answers
        time.sleep(12)
        shot(b, "[...document.querySelectorAll('.msg')].at(-1)")
        b.js("window.scrollTo(0, 0)")
        time.sleep(1)
        b.js("document.querySelector('section.try button.btn-primary').click()")  # the agent tries to decide
        b.wait("/Running in the sandbox/.test(document.querySelector('section.try')?.innerText || '')", timeout=60, every=0.3)
        b.wait("!/Running in the sandbox/.test(document.querySelector('section.try')?.innerText || '')", timeout=600)
        time.sleep(2)
        b.js("(() => { const box = document.querySelector('.log .lines'); "
             "const d = [...(box?.querySelectorAll('.line.deny') || [])].pop(); "
             "if (box && d) box.scrollTop += d.getBoundingClientRect().top - box.getBoundingClientRect().top - box.clientHeight / 3 })()")
        time.sleep(2)
        shot(b, "[...document.querySelectorAll('.log .line.deny')].pop() || document.querySelector('.log')")


def finish_page(path, label="Finish"):
    def finish():
        b = Tab()
        try:
            b.go(f"{record.DEVICE}{path}", settle=4)
            b.click_text(label, selector="button")
            b.wait("location.pathname === '/demo'", timeout=600, every=2)
        finally:
            b.close()
    return finish


CHAT = "document.querySelector('.chat.{side}')"
THINKING = "!!document.querySelector('.chat.{side} .thinking')"


def last_msg(side):
    return f"[...document.querySelectorAll('.chat.{side} .msg')].at(-1)"


def wait_answer(b, side, timeout=1500):
    """Until the agent has answered in that chat (the chat's 'working on it' line gone)."""
    b.wait(THINKING.format(side=side), timeout=30, every=0.5)
    b.wait(f"!({THINKING.format(side=side)})", timeout=timeout, every=2)
    time.sleep(3)


def sovereign_device():
    demo = "sovereign"
    with segment(demo, "device", f"{record.DEVICE}/demo/sovereign") as b:
        b.wait("!!document.querySelector('.chat.applicant .tries button:not([disabled])')", timeout=1800, every=5)
        time.sleep(5)
        shot(b, CHAT.format(side="applicant"))                          # the two chats, ready
        b.click_text("Write as", selector=".chat.applicant .tries button")
        wait_answer(b, "applicant")
        shot(b, last_msg("applicant"))                                  # the agent answers in Portuguese
        b.wait("!!document.querySelector('.chat.officer .opts button')", timeout=600, every=2)
        time.sleep(3)
        shot(b, last_msg("officer"))                                    # the assessment, in German
        b.click_text("approve it itself", selector=".chat.officer .tries button")
        wait_answer(b, "officer")
        shot(b, last_msg("officer"))                                    # refused: the officer decides
        b.click_text("GPT-4o", selector=".chat.officer .tries button")
        wait_answer(b, "officer")
        shot(b, last_msg("officer"))                                    # refused: EU models only
        b.js("document.querySelector('.chat.officer .opts button.btn-primary')?.click()")  # the officer confirms
        b.wait("!!document.querySelector('.chat.applicant .msg.letter')", timeout=600, every=2)
        time.sleep(4)
        shot(b, "document.querySelector('.chat.applicant .msg.letter')")  # the letter, in Portuguese
        shot(b, "document.querySelector('.log')")                       # what OpenShell allowed and refused


TERM = "document.querySelectorAll('.xterm-screen')[{n}]"


def devsandbox_device():
    demo = "developer-sandbox"
    with segment(demo, "device", f"{record.DEVICE}/demo/developer-sandbox") as b:
        b.wait("!!document.querySelector('.xterm-helper-textarea')", timeout=1200, every=3)
        time.sleep(4)
        shot(b, TERM.format(n=0))                                       # a terminal in the sandbox
        demos.term_type(b, "claude")
        time.sleep(6)
        if b.js(f"/trust this folder/i.test({demos.TERM_TEXT})"):
            demos.term_key(b, "ArrowDown", vk=40)
            time.sleep(0.5)
            demos.term_key(b, "Enter", vk=13)
        demos.term_wait(b, r"shift\+tab|for shortcuts|/effort", timeout=120)
        time.sleep(2)
        shot(b, TERM.format(n=0))                                       # Claude Code, on the platform's model
        demos.term_type(b, "Write fizzbuzz.py with a fizzbuzz(n) function and test_fizzbuzz.py with unittest "
                           "tests, then run: python3 -m unittest -v")
        time.sleep(4)
        demos.claude_done(b)
        time.sleep(2)
        shot(b, TERM.format(n=0))                                       # code written, tests passing
        demos.term_type(b, "Run this command and tell me what happened: curl -sS -m 8 https://www.suse.com")
        time.sleep(4)
        demos.claude_done(b, timeout=300)
        time.sleep(2)
        shot(b, TERM.format(n=0))                                       # denied by the sandbox
        demos.term_type(b, "/exit")
        time.sleep(4)
        demos.term_type(b, "clear")
        time.sleep(1)
        demos.term_type(b, demos.CURL)
        time.sleep(10)
        shot(b, TERM.format(n=0))                                       # curl: refused
        b.js("document.querySelector('details.policy summary')?.click()")  # the platform team's side
        b.wait("document.querySelectorAll('.xterm-helper-textarea').length >= 2", timeout=60)
        time.sleep(4)
        demos.term_type(b, demos.ALLOW, term=1, paste=True)
        demos.term_idle(b, quiet=4, timeout=120)
        demos.term_type(b, demos.CURL)
        time.sleep(10)
        shot(b, TERM.format(n=0))                                       # allowed, live
        demos.term_type(b, demos.REVOKE, term=1, paste=True)
        demos.term_idle(b, quiet=4, timeout=120)
        demos.term_type(b, demos.CURL)
        time.sleep(10)
        shot(b, TERM.format(n=0))                                       # revoked, live


def nav(path):
    return f"document.querySelector('nav a[href=\"{path}\"], a.nav-link[href=\"{path}\"]')"


def record_overview(parts):
    """SUSE AI Factory for developers: the developer's side, then SUSE AI Factory with NVIDIA in the Rancher Prime UI,
    then SUSE Observability. Deploys nothing."""
    demo = "developer-overview"
    parts = parts or ["device", "saif", "observability"]
    if "device" in parts:
        with segment(demo, "device", f"{record.DEVICE}/") as b:
            time.sleep(5)
            shot(b, text_el("Platform", "h2, h3"))                          # the platform at a glance
            b.js(f"{nav('/catalog')}.click()")
            time.sleep(5)
            shot(b, text_el("Fraud Detection & Investigation", "h3, h4"))   # ready-made Blueprints
            b.js(f"{nav('/workspace')}.click()")
            time.sleep(5)
            shot(b, text_el("NVIDIA Models (shared)", "h3, h4"))            # what is deployed, in plain terms
            b.js(f"{nav('/studio')}.click()")
            time.sleep(5)
            b.go(f"{record.DEVICE}/studio/new?aif={studio_id('finance')}", settle=4)
            b.wait(FLOW_READY, timeout=60)
            time.sleep(4)
            shot(b, "document.querySelector('.vue-flow__pane')")             # a Blueprint, drawn
            shot(b, node("agent"))                                          # its agent, configured
            b.click_text("YAML", selector="button")                         # the Blueprint as code
            time.sleep(3)
            shot(b, "document.querySelector('.vue-flow__pane')")
    if "saif" in parts:
        with segment(demo, "saif", f"{record.RANCHER}/dashboard/c/local/suseai/overview") as b:
            b.wait("/Total Workloads/.test(document.body.innerText)", timeout=90)
            time.sleep(3)
            b.click_text("Apps", selector="a")
            time.sleep(5)
            b.click_text("Blueprints", selector="a")
            time.sleep(5)
            b.js("(() => { const s = document.querySelector('select'); s.value = ''; s.dispatchEvent(new Event('change')) })()")
            time.sleep(3)
            b.click_text("Workloads", selector="a")
            time.sleep(5)
            b.click_text("Settings", selector="a")
            time.sleep(5)
            shot(b, "document.querySelector('h1, .title, header h2')")
    if "observability" in parts:
        so = record.OBSERVABILITY
        with segment(demo, "observability", so + "/#/views/urn:stackpack:aif-demos:component-presentation:blueprint") as b:
            b.wait("/Showing \\d+ Blueprints/.test(document.body.innerText)", timeout=90)
            pv.settle(b, 3)
            shot(b, text_el("Showing"))
            b.go(so + "/#/views/urn:stackpack:suse-ai:shared:query-view:genai-model", settle=2)
            b.wait("/Showing \\d+ models/.test(document.body.innerText)", timeout=60)
            pv.settle(b, 3)
            shot(b, text_el("Showing"))


def run(slug, parts):
    if slug == "developer-overview":
        record_overview(parts)
    elif slug == "secops":
        story(slug, parts, secops_device, lambda: finish_guided(slug), security=[("security-after", "ns-payments", "web")])
    elif slug == "traffic":
        story(slug, parts, traffic_device, finish_page("/demo/traffic"))
    elif slug == "sovereign":
        story(slug, parts, sovereign_device, finish_page("/demo/sovereign"))
    elif slug == "developer-sandbox":
        story(slug, parts, devsandbox_device, finish_page("/demo/developer-sandbox", "Stop and remove"),
              security=[("security", "ns-agents")])
    elif slug in demos.GUIDED:
        story(slug, parts, lambda: record_device_guided(slug), lambda: finish_guided(slug))
    else:
        raise SystemExit(f"no click path for {slug}")
