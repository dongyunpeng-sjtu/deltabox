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
from PIL import Image

# ───────── inputs ─────────
TRACE = Path(os.environ.get(
    "TRACE",
    "/home/dong/d-overlayfs/traces/swe-search/mimo/mcts/django__django-11095/nodes.json",
))
OUT_GIF = Path("/home/dong/deltabox-paper-website/assets/mcts_expansion.gif")
FPS = 4.0 / 1.5                # 1.5× slowdown — 375 ms per expansion frame
HOLD_END = 1                   # one final-hold frame, duration overridden below
FINAL_HOLD_MS = 3000           # 3 s pause on the resolved frame before looping

# ───────── colour scheme by MCTS state ─────────
# swe-search MCTS only emits these node states; EditCode is a transition
# inside PlanToCode and never lands as its own node, so it has no pill.
STATE_COLOR = {
    "Pending":      "#cbd5e1",  # slate (root)
    "SearchCode":   "#bfdbfe",  # light blue
    "PlanToCode":   "#fbcfe8",  # light pink — plan + apply patch
    "Finished":     "#bbf7d0",  # light green — candidate produced
    "Rejected":     "#fecaca",  # light red — pruned by simulator
}
EDGE_FILL_DEFAULT = "#1e293b"   # ring colour
HIGHLIGHT_RING = "#f59e0b"      # amber ring for newest node
ROLLBACK_COLOR = "#dc2626"      # red arrow showing checkpoint→restore jump


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
    "PlanToCode":   "Code",       # plan + edit happen in this state
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

    # harness eval result (sits beside nodes.json)
    harness = {}
    hs_path = TRACE.parent / "harness_score.json"
    if hs_path.exists():
        try:
            harness = json.loads(hs_path.read_text())
        except Exception:
            harness = {}
    resolved = bool(harness.get("resolved"))
    f2p_pass = len(harness.get("fail_to_pass", {}).get("success", []))
    f2p_fail = len(harness.get("fail_to_pass", {}).get("failure", []))
    p2p_pass = len(harness.get("pass_to_pass", {}).get("success", []))
    p2p_fail = len(harness.get("pass_to_pass", {}).get("failure", []))

    # figure sizing: scale with tree size, but cap at reasonable aspect
    fig_w = max(8.0, min(13.0, max_x * 0.55 + 2.0))
    fig_h = max(4.2, min(8.0,  (max_depth + 1) * 0.85 + 1.0))
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=120)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.86, bottom=0.14)

    fig.suptitle("MCTS node expansion (real SWE-bench trace)",
                 fontsize=13, fontweight="bold", x=0.02, ha="left", y=0.96)

    # The chosen patch comes from the highest-value Finished node.
    finished = [(nid, nodes[nid].get("value", 0.0))
                for nid in order if nodes[nid].get("state_name") == "Finished"]
    chosen_nid = max(finished, key=lambda t: t[1])[0] if finished else None

    # Winning trajectory: ancestor chain from root → chosen_nid.
    winning_path: list[int] = []
    if chosen_nid is not None:
        cur = chosen_nid
        while cur is not None:
            winning_path.append(cur)
            cur = nodes[cur].get("parent_id")
        winning_path.reverse()
    winning_set = set(winning_path)
    winning_edges = set(zip(winning_path, winning_path[1:]))  # (parent, child)

    legend_handles = [
        mpatches.Patch(color=STATE_COLOR[s], label=lbl, ec="#1e293b", lw=0.6)
        for s, lbl in [
            ("Pending", "Start"),
            ("SearchCode", "Search"),
            ("PlanToCode", "Code (plan+edit)"),
            ("Finished", "Finished"),
            ("Rejected", "Rejected"),
        ]
    ]
    fig.legend(handles=legend_handles, loc="lower center", ncol=5,
               bbox_to_anchor=(0.5, 0.01), frameon=False, fontsize=8)

    def draw_frame(i: int, is_final_hold: bool = False):
        ax.clear()
        ax.set_axis_off()
        added = set(order[:i + 1])
        latest = order[i]

        # 1) edges first (parent → child for each added node whose parent
        #    is also added). On the final hold frame, the winning path
        #    is drawn thicker in green underneath the regular edges.
        for nid in added:
            pid = nodes[nid].get("parent_id")
            if pid is None or pid not in added:
                continue
            x0, y0 = pos[pid]
            x1, y1 = pos[nid]
            on_path = is_final_hold and (pid, nid) in winning_edges
            if on_path:
                ax.plot([x0, x1], [y0, y1], color="#15803d", lw=3.4,
                        solid_capstyle="round", zorder=1.5, alpha=0.85)
            ax.plot([x0, x1], [y0, y1], color="#94a3b8", lw=0.9,
                    solid_capstyle="round", zorder=1)

        # 2) nodes as ellipses with label inside
        for nid in added:
            x, y = pos[nid]
            face = STATE_COLOR.get(nodes[nid]["state_name"], "#e2e8f0")
            if is_final_hold and nid == chosen_nid:
                ring, lw = "#15803d", 2.6           # thick green = chosen patch
            elif is_final_hold and nid in winning_set:
                ring, lw = "#16a34a", 1.8           # green = on winning path
            elif nid == latest and not is_final_hold:
                ring, lw = HIGHLIGHT_RING, 1.6      # amber = newest
            else:
                ring, lw = EDGE_FILL_DEFAULT, 0.6
            el = mpatches.FancyBboxPatch(
                (x - 0.45, y - 0.27), 0.9, 0.54,
                boxstyle="round,pad=0.02,rounding_size=0.18",
                linewidth=lw, edgecolor=ring, facecolor=face, zorder=2)
            ax.add_patch(el)
            ax.text(x, y, node_label(nodes, nid),
                    ha="center", va="center", fontsize=7.2,
                    color="#0c1320", zorder=3)

        # 2b) rollback arrow: from the previously-active leaf to the
        #     parent we restored into before expanding `latest`.
        rollback_text = ""
        if i > 0 and not is_final_hold:
            prev = order[i - 1]
            target = nodes[latest].get("parent_id")
            if target is not None and target != prev and target in added:
                x0, y0 = pos[prev]
                x1, y1 = pos[target]
                # bow outward so the curve doesn't slice through the tree.
                rad = 0.35 if x0 <= x1 else -0.35
                arrow = mpatches.FancyArrowPatch(
                    (x0, y0 + 0.05), (x1, y1 - 0.05),
                    arrowstyle="-|>",
                    connectionstyle=f"arc3,rad={rad}",
                    color=ROLLBACK_COLOR, lw=2.0,
                    mutation_scale=15,
                    shrinkA=14, shrinkB=14,
                    zorder=4, alpha=0.9,
                )
                ax.add_patch(arrow)
                # label near the midpoint of the chord, nudged perpendicular
                mx, my = (x0 + x1) / 2, (y0 + y1) / 2
                dx, dy = (x1 - x0), (y1 - y0)
                L = (dx * dx + dy * dy) ** 0.5 or 1.0
                # perpendicular unit vector, sign aligned with rad
                px, py = -dy / L, dx / L
                offset = 0.55 * (1 if rad >= 0 else -1)
                ax.text(mx + px * offset, my + py * offset,
                        f"rollback {prev}→{target}",
                        ha="center", va="center", fontsize=7.5,
                        color=ROLLBACK_COLOR, fontweight="bold",
                        zorder=5)
                rollback_text = f"    [rollback {prev}→{target}]"

        # 3) framing
        ax.set_xlim(-0.7, max_x + 0.7)
        ax.set_ylim(-max_depth - 0.8, 0.8)
        if is_final_hold:
            badge_top = f"patch from node {chosen_nid}"
            badge_bot = (
                f"fail→pass {f2p_pass}/{f2p_pass + f2p_fail}  ·  "
                f"pass→pass {p2p_pass}/{p2p_pass + p2p_fail}"
                if resolved else "best of the explored branches"
            )
            ax.set_title(
                f"trace = {instance}    final tree: {n_nodes} nodes, depth {max_depth}",
                fontsize=9.8,
                fontweight="bold",
                loc="left",
                color="#1f2330",
                pad=4,
            )
            # Resolved badge — sized to fit the empty area immediately
            # to the LEFT of the chosen Finished node.
            banner_color = "#16a34a" if resolved else "#b91c1c"
            banner_face = "#dcfce7" if resolved else "#fee2e2"
            mark = "✓ RESOLVED" if resolved else "✗ NOT RESOLVED"
            # Empty grid slot to the left of #19 spans x∈[4,9] across depths
            # 4-7; size + center the banner inside that rectangle.
            box_w, box_h = 4.8, 2.7
            if chosen_nid is not None:
                chx, chy = pos[chosen_nid]
                cx = chx - 4.1            # banner right edge ~ x=8.8 (left of #16)
                cy = chy + 2.4            # banner y range ~ [-7, -4.3]
            else:
                cx, cy = max_x / 2, -max_depth / 2
            banner = mpatches.FancyBboxPatch(
                (cx - box_w / 2, cy - box_h / 2), box_w, box_h,
                boxstyle="round,pad=0.05,rounding_size=0.3",
                linewidth=3.0, edgecolor=banner_color,
                facecolor=banner_face, alpha=0.96, zorder=10,
            )
            ax.add_patch(banner)
            ax.text(cx, cy + box_h * 0.28, mark,
                    ha="center", va="center",
                    fontsize=22, fontweight="bold",
                    color=banner_color, zorder=11)
            ax.text(cx, cy - box_h * 0.05, badge_top,
                    ha="center", va="center",
                    fontsize=10.5, color="#14532d" if resolved else "#7f1d1d",
                    zorder=11)
            ax.text(cx, cy - box_h * 0.28, badge_bot,
                    ha="center", va="center",
                    fontsize=8.5, color="#14532d" if resolved else "#7f1d1d",
                    zorder=11)
        else:
            ax.set_title(
                f"trace = {instance}    iter {i + 1} / {n_nodes}    "
                f"latest = node {latest} ({nodes[latest]['state_name']}, "
                f"depth {nodes[latest]['depth']}, visits {nodes[latest]['visits']})"
                + rollback_text,
                fontsize=9.5, loc="left", color="#1f2330", pad=4,
            )
        return []

    total_frames = n_nodes + HOLD_END
    def frame_fn(f):
        return draw_frame(min(f, n_nodes - 1), is_final_hold=(f >= n_nodes))

    anim = FuncAnimation(fig, frame_fn, frames=total_frames,
                         interval=int(1000 / FPS), blit=False)
    OUT_GIF.parent.mkdir(parents=True, exist_ok=True)
    writer = PillowWriter(fps=FPS)
    anim.save(str(OUT_GIF), writer=writer)
    plt.close(fig)

    # Post-process: extend the last (final-hold) frame to FINAL_HOLD_MS.
    # PillowWriter only supports a uniform per-frame duration, so re-save
    # with a per-frame duration list.
    im = Image.open(OUT_GIF)
    per_frame_dur = int(1000 / FPS)
    frames, durations = [], []
    idx = 0
    while True:
        try:
            im.seek(idx)
        except EOFError:
            break
        frames.append(im.copy())
        durations.append(per_frame_dur)
        idx += 1
    if frames:
        durations[-1] = FINAL_HOLD_MS
        frames[0].save(
            OUT_GIF, save_all=True, append_images=frames[1:],
            duration=durations, loop=0, optimize=False, disposal=2,
        )
    print(f"wrote {OUT_GIF} ({OUT_GIF.stat().st_size/1024:.0f} KB, "
          f"{n_nodes} nodes, {len(frames)} frames @ {per_frame_dur} ms "
          f"+ {FINAL_HOLD_MS} ms hold, fig={fig_w:.1f}x{fig_h:.1f})")


if __name__ == "__main__":
    make_animation()
