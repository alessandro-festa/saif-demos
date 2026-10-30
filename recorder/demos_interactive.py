"""The click paths of each demo, segment by segment. Every click is a step of the demo; shot() adds a
step where the page has something to show but nothing needs clicking."""
import time

import demos
import guided
import platform_videos as pv
import record

from interactive import segment, shot, text_el

# The Studio flow of each guided demo: its Blueprint as the Studio opens it.
STUDIO = {
    "manufacturing": "factory-operations-visual-inspection-0-4-0",
    "finance": "fraud-detection-investigation-0-3-0",
    "telco": "network-configuration-autonomous-operations-0-3-0",
    "retail": "conversational-shopping-assistant-0-3-0",
    "healthcare": "ambient-clinical-documentation-0-3-1",
    "secops": "sovereign-agentic-secops-0-3-0",
}


class NoMarks:
    def mark(self, name):
        pass


def node(kind):
    return f"document.querySelector('.fnode.k-{kind}')"


FLOW_READY = "document.querySelectorAll('.vue-flow__node').length > 3"


def record_flow(demo):
    """The use case's Blueprint in the Studio: the whole flow, the agent, the model, what lies outside."""
    with segment(demo, "flow", f"{record.DEVICE}/studio/new?aif={STUDIO[demo]}") as b:
        b.wait(FLOW_READY, timeout=60)
        time.sleep(4)
        shot(b, "document.querySelector('.vue-flow__pane')")  # the whole flow
        shot(b, node("agent"))           # the agent in its NVIDIA OpenShell sandbox
        shot(b, node("model"))           # the NVIDIA NIM it calls
        shot(b, node("external"))        # what the sandbox refuses


def record_device(demo):
    """Deploy the use case through SUSE AI Factory with NVIDIA, then each step's runs and their results."""
    g = demos.GUIDED[demo]
    demos.warm(demos.MODELS[demo])
    pv.clear_results(demo)
    with segment(demo, "device", f"{record.DEVICE}/demo/{demo}?step=1") as b:
        b.wait("!!document.querySelector('.step-link')", timeout=60)
        time.sleep(3)
        b.click_text("Deploy the use case")
        shot(b, text_el("SUSE AI Factory · ready"),
             "document.body.innerText.includes('SUSE AI Factory · ready') && /sandbox · Ready/.test(document.body.innerText)")
        for title, runs in g["runs"]:
            guided.step(b, NoMarks(), title)
            for label in runs:
                guided.run(b, NoMarks(), label, dwell=1)
                block = guided.RUN_BLOCK.format(label=f'"{label}"')
                shot(b, f"(() => {{ const c = ({block})?.querySelectorAll('.cells > *'); return c?.[c.length - 1] }})()")


def record_rancher(demo, workload):
    """SUSE AI Factory with NVIDIA in the Rancher Prime UI: the overview, the workloads, the demo's own."""
    with segment(demo, "rancher", f"{record.RANCHER}/dashboard/c/local/suseai/overview") as b:
        b.wait("/Total Workloads/.test(document.body.innerText)", timeout=90)
        time.sleep(3)
        b.click_text("Workloads", selector="a")
        b.wait(f"/{workload}/.test(document.body.innerText)", timeout=60)
        time.sleep(3)
        b.click_text(workload, selector="a")
        time.sleep(6)
        shot(b, "document.querySelector('h1, .title, header h2')")


def record_observability(demo):
    """SUSE Observability: the Blueprints, this one and its flow, the agent's trace and span, the models,
    the live dashboard."""
    p = pv.PLATFORM[demo]
    so = record.OBSERVABILITY
    with segment(demo, "observability", so + "/#/views/urn:stackpack:aif-demos:component-presentation:blueprint") as b:
        b.wait("/Showing \\d+ Blueprints/.test(document.body.innerText)", timeout=90)
        pv.settle(b, 3)
        shot(b, text_el(p["name"]))
        b.go(so + f"/#/components/urn:aif:blueprint:{p['blueprint']}", settle=2)
        b.wait("/Flow: what it is made of/.test(document.body.innerText)", timeout=60)
        pv.settle(b, 3)
        pv.click_link(b, "Flow: what it is made of")
        b.wait("!!document.querySelector('svg g, canvas') && /Topology/.test(document.body.innerText)", timeout=60)
        time.sleep(9)
        shot(b, "document.querySelector('svg g, canvas')")
        b.go(so + f"/#/components/urn:opentelemetry:namespace%2Fns-agents:service%2F{p['agent']}/traces", settle=2)
        b.wait("/traces matching/.test(document.body.innerText)", timeout=60)
        pv.settle(b, 3)
        pv.click_leaf(b, p.get("trace", "/^agent: /"))
        time.sleep(6)
        if p.get("span", "/→ tool/"):
            pv.click_leaf(b, p.get("span", "/→ tool/"))
            time.sleep(4)
        b.js(pv.EXPAND_ATTRIBUTES)
        time.sleep(1)
        b.js(pv.UNSCROLL)
        time.sleep(5)
        shot(b, text_el("Span attributes"))
        b.go(so + "/#/views/urn:stackpack:suse-ai:shared:query-view:genai-model", settle=2)
        b.wait("/Showing \\d+ models/.test(document.body.innerText)", timeout=60)
        pv.settle(b, 3)
        shot(b, text_el("Showing"))
        b.go(so + "/#/dashboards/urn:stackpack:aif-demos:shared:dashboard:live", settle=2)
        b.wait("/Agent requests allowed/.test(document.body.innerText)", timeout=60)
        time.sleep(9)
        shot(b, text_el("Agent requests allowed"))


def finish(demo):
    from interactive import Tab
    b = Tab()
    try:
        guided.finish(b, demo)
    finally:
        b.close()


def record_guided(demo, parts):
    g = demos.GUIDED[demo]
    parts = parts or ["flow", "device", "rancher", "observability", "finish"]
    if "flow" in parts:
        record_flow(demo)
    if "device" in parts:
        record_device(demo)
        time.sleep(30)  # the agent's traces and the Blueprint's health reach SUSE Observability
    if "rancher" in parts:
        record_rancher(demo, g["workload"])
    if "observability" in parts:
        record_observability(demo)
    if "finish" in parts:
        finish(demo)


def run(slug, parts):
    if slug in demos.GUIDED and slug != "secops":
        record_guided(slug, parts)
    else:
        raise SystemExit(f"no click path for {slug} yet")
