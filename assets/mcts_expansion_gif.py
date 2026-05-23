#!/usr/bin/env python3
"""mcts_expansion_gif.py — animate MCTS node expansion from a real trace.

Reads a `nodes.json` (the post-run MCTS tree dump produced by SWE-search),
orders nodes by their integer id (= creation order), and writes a GIF
where each frame adds the next node to the tree and highlights it.

Output: assets/mcts_expansion.gif
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.animation import FuncAnimation, PillowWriter
import networkx as nx

# ───────── inputs ─────────
TRACE = Path(os.environ.get(
    "TRACE",
    "/home/dong/d-overlayfs/traces/swe-search/mimo/mcts/django__django-11095/nodes.json"
))
OUT_GIF = Path("/home/dong/deltabox-paper-website/assets/mcts_expansion.gif")
FPS = 4.0     # 4 frames/sec ⇒ ~10 s for 40 nodes
HOLD_END = 2  # extra frames at the end so the final tree lingers

# ───────── colour scheme by MCTS state ─────────
STATE_COLOR = {
    "Pending":      "#94a3b8",  # slate (root)
    "SearchCode":   "#60a5fa",  # blue (search)
    "IdentifyCode": "#3b82f6",
    "PlanToCode":   "#a78bfa",  # purple (plan)
    "EditCode":     "#fb923c",  # orange (edit)
    "Finished":     "#22c55e",  # green (terminal pass)
    "Rejected":     "#ef4444",  # red (terminal fail)
}
DEFAULT_COLOR = "#cbd5e1"
EDGE_COLOR = "#475569"
HIGHLIGHT = "#fbbf24"   # newly-added node gets a yellow ring


def load_tree(path: Path):
    raw = json.loads(path.read_text())
    # keys are stringified ints; convert + sort by id (= creation order)
    nodes = {int(k): v for k, v in raw.items()}
    order = sorted(nodes)
    return nodes, order


def tree_layout(nodes: dict[int, dict]) -> dict[int, tuple[float, float]]:
    """Layered (left→right) layout: x = depth, y = vertical slot.

    Slot assigned by DFS over the parent → children chain so siblings
    don't overlap. Works for trees up to ~200 nodes without overlap.
    """
    pos: dict[int, tuple[float, float]] = {}
    children: dict[int, list[int]] = {nid: list(n.get("children_ids") or []) for nid, n in nodes.items()}
    # find root (no parent)
    root = next(nid for nid, n in nodes.items() if n.get("parent_id") is None)
    slot = [0]

    def dfs(nid: int):
        ch = sorted(children.get(nid, []), key=lambda c: c)
        if not ch:
            y = slot[0]
            slot[0] += 1
        else:
            ys = []
            for c in ch:
                if c in nodes:
                    dfs(c)
                    ys.append(pos[c][1])
            y = sum(ys) / len(ys) if ys else slot[0]
        x = nodes[nid]["depth"]
        pos[nid] = (x, -y)  # negative so the tree grows downward

    dfs(root)
    return pos


def make_animation():
    nodes, order = load_tree(TRACE)
    pos = tree_layout(nodes)
    instance = TRACE.parent.name

    # Build the full directed graph once; we'll subset by frame.
    G_full = nx.DiGraph()
    for nid, n in nodes.items():
        G_full.add_node(nid)
        pid = n.get("parent_id")
        if pid is not None and pid in nodes:
            G_full.add_edge(pid, nid)

    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=120)
    fig.subplots_adjust(left=0.04, right=0.96, top=0.90, bottom=0.18)

    fig.suptitle("MCTS node expansion (real SWE-bench trace)",
                 fontsize=13, fontweight="bold", x=0.04, ha="left")

    # state-color legend
    handles = [
        mpatches.Patch(color=STATE_COLOR[s], label=s)
        for s in ["Pending", "SearchCode", "PlanToCode", "EditCode", "Finished", "Rejected"]
    ]
    fig.legend(handles=handles, loc="lower center", ncol=6,
               bbox_to_anchor=(0.5, 0.02), frameon=False, fontsize=8)

    def draw_frame(i: int):
        ax.clear()
        ax.set_axis_off()
        added = order[:i + 1]
        sub = G_full.subgraph(added)
        edge_list = list(sub.edges())
        # nodes
        node_colors = [STATE_COLOR.get(nodes[nid]["state_name"], DEFAULT_COLOR) for nid in added]
        node_sizes = [
            120 + 18 * min(nodes[nid].get("visits", 0), 30)
            for nid in added
        ]
        nx.draw_networkx_edges(sub, pos, ax=ax, edge_color=EDGE_COLOR,
                               width=1.0, arrows=False, alpha=0.55)
        nx.draw_networkx_nodes(sub, pos, ax=ax, nodelist=added,
                               node_color=node_colors,
                               node_size=node_sizes,
                               edgecolors="#1e293b", linewidths=0.6)
        # highlight newest node
        latest = order[i]
        nx.draw_networkx_nodes(sub, pos, ax=ax, nodelist=[latest],
                               node_color=HIGHLIGHT,
                               node_size=node_sizes[-1] + 220,
                               edgecolors="#92400e", linewidths=1.6, alpha=0.55)
        # annotate latest with its id
        x, y = pos[latest]
        ax.annotate(f"node {latest} ({nodes[latest]['state_name']})",
                    xy=(x, y), xytext=(8, 10), textcoords="offset points",
                    fontsize=9, color="#1e293b",
                    arrowprops=dict(arrowstyle="-", color="#475569", lw=0.6))

        # Right padding bumped so the "node N (State)" annotation doesn't
        # clip when the latest node sits at max depth.
        ax.set_xlim(-0.6, max(n["depth"] for n in nodes.values()) + 2.4)
        ys = [p[1] for p in pos.values()]
        ax.set_ylim(min(ys) - 0.6, max(ys) + 0.6)
        ax.set_title(
            f"trace = {instance}    iter {i + 1} / {len(order)}    "
            f"depth = {nodes[latest]['depth']}    visits = {nodes[latest]['visits']}",
            fontsize=10, loc="left", color="#1f2330", pad=4,
        )
        return []

    total_frames = len(order) + HOLD_END
    def frame_fn(f):
        return draw_frame(min(f, len(order) - 1))

    anim = FuncAnimation(fig, frame_fn, frames=total_frames,
                         interval=int(1000 / FPS), blit=False)
    OUT_GIF.parent.mkdir(parents=True, exist_ok=True)
    writer = PillowWriter(fps=FPS)
    anim.save(str(OUT_GIF), writer=writer)
    plt.close(fig)
    print(f"wrote {OUT_GIF} ({OUT_GIF.stat().st_size/1024:.0f} KB, {len(order)} nodes, {total_frames} frames)")


if __name__ == "__main__":
    make_animation()
