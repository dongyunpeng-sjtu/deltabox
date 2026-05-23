#!/usr/bin/env python3
"""mcts_expansion_gif.py — animate MCTS node expansion from a real trace.

Top-down hierarchical layout (depth=0 at top). Each subtree's horizontal
slot is proportional to its leaf count, so siblings never overlap and the
shape stays readable as the tree grows.

Inputs : a SWE-search `nodes.json` (dict {id: {parent_id, children_ids,
         depth, state_name, visits, ...}})
Output : assets/mcts_expansion.gif
"""
from __future__ import annotations
import json, os
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.animation import FuncAnimation, PillowWriter

# ───────── inputs ─────────
TRACE = Path(os.environ.get(
    "TRACE",
    "/home/dong/d-overlayfs/traces/swe-search/mimo/mcts/django__django-11095/nodes.json",
))
OUT_GIF = Path("/home/dong/deltabox-paper-website/assets/mcts_expansion.gif")
FPS = 4.0
HOLD_END = 4

# ───────── colour scheme by MCTS state (matches reference design) ─────────
STATE_COLOR = {
    "Pending":      "#cbd5e1",  # slate (root)
    "SearchCode":   "#bfdbfe",  # light blue
    "IdentifyCode": "#93c5fd",
    "PlanToCode":   "#fbcfe8",  # light pink (matches reference's "Plan" pill)
    "EditCode":     "#c7d2fe",  # light indigo (matches reference's "Edit" pill)
    "Finished":     "#bbf7d0",  # light green
    "Rejected":     "#fecaca",  # light red
}
EDGE_FILL_DEFAULT = "#1e293b"   # ring colour
HIGHLIGHT_RING = "#f59e0b"      # amber ring for newest node


# ───────── tree layout (recursive leaf-count based) ─────────

def compute_layout(nodes: dict[int, dict]) -> dict[int, tuple[float, float]]:
    """Return {id: (x, y)} where y = -depth (top-down) and x is a
    subtree-width-proportional slot."""
    root = next(nid for nid, n in nodes.items() if n.get("parent_id") is None)
    children = {nid: [c for c in (n.get("children_ids") or []) if c in nodes]
                for nid, n in nodes.items()}

    # 1) leaf-count per subtree
    leaves: dict[int, int] = {}

    def count_leaves(nid: int) -> int:
        ch = children.get(nid, [])
        if not ch:
            leaves[nid] = 1
            return 1
        s = sum(count_leaves(c) for c in ch)
        leaves[nid] = max(1, s)
        return leaves[nid]

    count_leaves(root)

    # 2) recursive x placement: each subtree spans [x_start, x_start+leaves)
    pos: dict[int, tuple[float, float]] = {}

    def place(nid: int, x_start: float):
        span = leaves[nid]
        ch = children.get(nid, [])
        if not ch:
            pos[nid] = (x_start + 0.5, -nodes[nid]["depth"])
            return
        # children get consecutive slots
        cursor = x_start
        for c in ch:
            place(c, cursor)
            cursor += leaves[c]
        # parent centred over its children's centroid
        cx = sum(pos[c][0] for c in ch) / len(ch)
        pos[nid] = (cx, -nodes[nid]["depth"])

    place(root, 0.0)
    return pos


# ───────── label helper ─────────
SHORT_STATE = {
    "Pending":      "Start",
    "SearchCode":   "Search",
    "IdentifyCode": "Find",
    "PlanToCode":   "Plan",
    "EditCode":     "Edit",
    "Finished":     "Finished",
    "Rejected":     "Rejected",
}


def node_label(nodes: dict[int, dict], nid: int) -> str:
    s = nodes[nid]["state_name"]
    return f"{SHORT_STATE.get(s, s)}\n#{nid}"


# ───────── animation ─────────

def make_animation():
    raw = json.loads(TRACE.read_text())
    nodes = {int(k): v for k, v in raw.items()}
    order = sorted(nodes)            # creation order
    pos = compute_layout(nodes)
    instance = TRACE.parent.name
    n_nodes = len(order)
    max_depth = max(n["depth"] for n in nodes.values())
    max_x = max(p[0] for p in pos.values())

    # figure sizing: scale with tree size, but cap at reasonable aspect
    fig_w = max(8.0, min(13.0, max_x * 0.55 + 2.0))
    fig_h = max(4.2, min(8.0,  (max_depth + 1) * 0.85 + 1.0))
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=120)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.86, bottom=0.14)

    fig.suptitle("MCTS node expansion (real SWE-bench trace)",
                 fontsize=13, fontweight="bold", x=0.02, ha="left", y=0.96)

    legend_handles = [
        mpatches.Patch(color=STATE_COLOR[s], label=lbl, ec="#1e293b", lw=0.6)
        for s, lbl in [
            ("Pending", "Start"),
            ("SearchCode", "Search"),
            ("PlanToCode", "Plan"),
            ("EditCode", "Edit"),
            ("Finished", "Finished"),
            ("Rejected", "Rejected"),
        ]
    ]
    fig.legend(handles=legend_handles, loc="lower center", ncol=6,
               bbox_to_anchor=(0.5, 0.01), frameon=False, fontsize=8)

    def draw_frame(i: int):
        ax.clear()
        ax.set_axis_off()
        added = set(order[:i + 1])
        latest = order[i]

        # 1) edges first (parent → child for each added node whose parent
        #    is also added)
        for nid in added:
            pid = nodes[nid].get("parent_id")
            if pid is None or pid not in added:
                continue
            x0, y0 = pos[pid]
            x1, y1 = pos[nid]
            ax.plot([x0, x1], [y0, y1], color="#94a3b8", lw=0.9,
                    solid_capstyle="round", zorder=1)

        # 2) nodes as ellipses with label inside
        for nid in added:
            x, y = pos[nid]
            face = STATE_COLOR.get(nodes[nid]["state_name"], "#e2e8f0")
            ring = HIGHLIGHT_RING if nid == latest else EDGE_FILL_DEFAULT
            lw = 1.6 if nid == latest else 0.6
            el = mpatches.FancyBboxPatch(
                (x - 0.45, y - 0.27), 0.9, 0.54,
                boxstyle="round,pad=0.02,rounding_size=0.18",
                linewidth=lw, edgecolor=ring, facecolor=face, zorder=2)
            ax.add_patch(el)
            ax.text(x, y, node_label(nodes, nid),
                    ha="center", va="center", fontsize=7.2,
                    color="#0c1320", zorder=3)

        # 3) framing
        ax.set_xlim(-0.7, max_x + 0.7)
        ax.set_ylim(-max_depth - 0.8, 0.8)
        ax.set_title(
            f"trace = {instance}    iter {i + 1} / {n_nodes}    "
            f"latest = node {latest} ({nodes[latest]['state_name']}, "
            f"depth {nodes[latest]['depth']}, visits {nodes[latest]['visits']})",
            fontsize=9.5, loc="left", color="#1f2330", pad=4,
        )
        return []

    total_frames = n_nodes + HOLD_END
    def frame_fn(f):
        return draw_frame(min(f, n_nodes - 1))

    anim = FuncAnimation(fig, frame_fn, frames=total_frames,
                         interval=int(1000 / FPS), blit=False)
    OUT_GIF.parent.mkdir(parents=True, exist_ok=True)
    writer = PillowWriter(fps=FPS)
    anim.save(str(OUT_GIF), writer=writer)
    plt.close(fig)
    print(f"wrote {OUT_GIF} ({OUT_GIF.stat().st_size/1024:.0f} KB, "
          f"{n_nodes} nodes, {total_frames} frames, fig={fig_w:.1f}x{fig_h:.1f})")


if __name__ == "__main__":
    make_animation()
