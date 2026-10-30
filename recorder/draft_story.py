#!/usr/bin/env python3
"""A first draft of a demo's story (stories/<slug>.json) from its recordings and, for the guided demos, the words
the demo videos say over each run (aif-dev docs/videos/demos.py GUIDED). Edit the draft by hand after.

    python3 recorder/draft_story.py <slug>

The chapters follow the recorder's story: the architecture (Studio), SUSE AI Factory with NVIDIA deploying the
Blueprint, Fleet rolling it out, the demo's own UI, from SUSE AI Factory with NVIDIA into Rancher, SUSE Security
where the use case needs it, SUSE Observability.
"""
import json
import sys
from pathlib import Path

import interactive  # noqa: F401  (puts aif-dev's docs/videos on the path)
import demos
import demos_interactive as di

ROOT = Path(__file__).resolve().parent.parent


def captured(slug, segment):
    found = list((ROOT / "recordings" / slug / segment).glob("*/demo.config.json"))
    return json.loads(found[0].read_text())["steps"] if found else []


def numbered(texts, at=None):
    """Step texts by number; None drops the step; at: {number: (x, y)} moves a hotspot."""
    steps = {str(i + 1): ({"drop": True} if t is None else {"text": t}) for i, t in enumerate(texts)}
    for n, (x, y) in (at or {}).items():
        steps[str(n)].update({"x": x, "y": y})
    return steps


def flow_steps(name):
    return numbered([
        f"The architecture of **{name}**, as the Studio draws it: the agent in its **NVIDIA OpenShell sandbox**, the "
        "systems it works with, the shared **NVIDIA** models and the people who decide. Green lines are allowed, red "
        "ones refused by the sandbox's policy.",
        "The **agent**: a NeMo Agent Toolkit agent, packaged as one component of the Blueprint. Its sandbox, providers "
        "and policy deploy with it.",
        "It reasons with an **NVIDIA NIM** shared by every use case from the *NVIDIA Models (shared)* Blueprint: "
        "downloaded once, always up.",
        "Everything else is **outside**: the sandbox refuses it. Enforced by policy, not promised in a prompt.",
    ])


def saif_steps(name):
    return numbered([
        f"The Blueprints of **SUSE AI Factory with NVIDIA**, SUSE's and its partners'. Open **{name}**.",
        "What the Blueprint brings: its versions, its description and its applications. **Install** it.",
        "The install wizard: the instance's name and its default namespace.",
        "Where it runs: a **Fleet Bundle** on the selected cluster.",
        "Each component's configuration can be changed here, or left as the Blueprint ships it.",
        "Review, then **Install**.",
        "**Install**: SUSE AI Factory with NVIDIA schedules the Blueprint on the cluster, through Fleet.",
        None,
        None,
        f"**{name}** is now a workload of SUSE AI Factory with NVIDIA, its components rolling out.",
    ])


def fleet_steps(name):
    return numbered([
        f"In **Continuous Delivery**, Fleet holds one bundle per component of **{name}**, each active on its cluster.",
        "One bundle in detail: the Kubernetes resources it deployed, and their state.",
    ], at={2: (0.62, 0.42)})


def guided_device_steps(slug):
    g = demos.GUIDED[slug]
    says = {f.split(":", 1)[1]: words for f, _, words in g["says"]}
    texts = ["The use case's own page: the Blueprint is **ready** in SUSE AI Factory with NVIDIA and the agent's sandbox "
             "is up. The log on the right is OpenShell's: every request the agent makes, allowed or denied."]
    for title, runs in g["runs"]:
        texts.append(f"Next: **{title}**.")
        for label in runs:
            texts.append(f"**{label}**: running in the agent's sandbox now.")
            if label in says:
                texts.append(says[label])
            elif "try to" in label.lower() and "internet" not in label.lower():
                texts.append("OpenShell's answer: **403, policy denied**. Enforced by policy, not promised in a prompt.")
            elif "internet" in label.lower():
                texts.append("**Blocked**, every time, and logged in red: the data stays on the customer's own infrastructure.")
            else:
                texts.append(f"The result of **{label.lower()}**, computed inside the agent's sandbox.")
    return numbered(texts)


def rancher_steps(name):
    return numbered([
        f"Back in SUSE AI Factory with NVIDIA: open the **{name}** workload.",
        "Its details: the Blueprint and version it comes from, where it runs, and the Fleet resources underneath. From "
        "here, straight into Rancher.",
        "The use case's namespace in Rancher: every resource, its state. Open **Workloads**.",
        "The use case's workloads. Open one.",
        "The deployment and its pods, live, with everything Rancher offers to inspect and operate it.",
    ], at={5: (0.3, 0.45)})


def observability_steps(name):
    return numbered([
        f"**SUSE Observability** lists every Blueprint deployed through SUSE AI Factory with NVIDIA, with its health. "
        f"Open **{name}**.",
        "The Blueprint as a component, right now: its health and events, with links to the agent's traces and to "
        "**Flow: what it is made of**.",
        "The same flow as in the Studio, live: each running component coloured by its health.",
    ])


def chapters(slug, name, device_steps):
    out = [
        {"id": "flow", "title": "The architecture",
         "blurb": f"{name} is a Blueprint in SUSE AI Factory with NVIDIA. The Studio shows what it is made of.",
         "segments": [{"name": "flow", "steps": flow_steps(name)}]},
        {"id": "saif", "title": "Deploy with SUSE AI Factory with NVIDIA",
         "blurb": "It is a Blueprint in SUSE AI Factory with NVIDIA. The SUSE AI Factory with NVIDIA UI is an extension "
                  "of the Rancher Prime UI, and it can also be consumed via API. Here it deploys the Blueprint.",
         "segments": [{"name": "saif", "steps": saif_steps(name)}]},
        {"id": "fleet", "title": "Rolled out by Fleet",
         "blurb": "SUSE AI Factory with NVIDIA deploys through Fleet, Rancher's GitOps engine: the same Blueprint on "
                  "one cluster or many.",
         "segments": [{"name": "fleet", "steps": fleet_steps(name)}]},
        {"id": "demo", "title": "The use case at work",
         "blurb": "The use case's own page, step by step: what the agent does, and what it is not allowed to do.",
         "segments": [{"name": "device", "steps": device_steps}]},
        {"id": "rancher", "title": "Into Rancher",
         "blurb": "From SUSE AI Factory with NVIDIA into Rancher, to understand the workload: its resources, its "
                  "namespace, its pods.",
         "segments": [{"name": "rancher", "steps": rancher_steps(name)}]},
        {"id": "observability", "title": "SUSE Observability",
         "blurb": "SUSE Observability shows the Blueprint's workload as it is right now: its health, its events and "
                  "its flow.",
         "segments": [{"name": "observability", "steps": observability_steps(name)}]},
    ]
    return out


def draft(slug):
    name = di.BLUEPRINT[slug][2]
    if slug in demos.GUIDED:
        g = demos.GUIDED[slug]
        title, sub = g["title"]
        intro = g["flow"].replace("Here's what we'll see. ", "")
        close = g["close"].replace("as a SUSE Blueprint on SUSE AI Factory with NVIDIA",
                                   "deployed as a Blueprint through SUSE AI Factory with NVIDIA").replace("deployed deployed", "deployed")
        dev = guided_device_steps(slug)
    else:
        title, sub, intro, close = name, "SUSE AI Factory with NVIDIA", "", ""
        dev = numbered(["The result."] * len(captured(slug, "device")))
    n = len(captured(slug, "device"))
    if n and len(dev) != n:
        print(f"warning: {n} device steps recorded, {len(dev)} drafted: check the numbering", file=sys.stderr)
    story = {"title": title, "subtitle": sub.replace("  ·  ", " · "), "intro": intro,
             "chapters": chapters(slug, name, dev),
             "outro": {"title": "A person stays in charge", "description": close}}
    out = ROOT / "stories" / f"{slug}.json"
    if out.exists():
        story["id"] = json.loads(out.read_text()).get("id")
    out.write_text(json.dumps(story, indent=2, ensure_ascii=False) + "\n")
    print(f"drafted {out.relative_to(ROOT)}")


if __name__ == "__main__":
    draft(sys.argv[1])
