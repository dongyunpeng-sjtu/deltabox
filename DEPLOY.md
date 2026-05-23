# DeltaBox &mdash; Paper Landing Page

Static project page for the paper
*DeltaBox: Scaling Stateful AI Agents with Millisecond-Level Sandbox
Checkpoint/Rollback*.

Single-page site, no JavaScript framework, no build step.

## File layout

```
.
├── index.html            # the page itself
├── style.css             # all styles
├── assets/
│   ├── deltabox-paper.pdf   # full paper (download link)
│   ├── fig1_overview.png    # Figure 1 - architecture
│   ├── fig_cdf.png          # per-event latency CDF
│   ├── fig_end2end.png      # end-to-end MCTS time
│   └── fig_rl_combo.png     # RL fan-out characterisation
└── README.md
```

## Local preview

```
cd ~/deltabox-paper-website
python3 -m http.server 8080
# open http://localhost:8080
```

## Publishing to GitHub Pages

This site is intended for a `*.github.io` repo (user or project page).
Code is **not** open-sourced &mdash; only the paper PDF, figures, and
this landing page are published. Source code, kernel patches, and
benchmark scaffolding are kept private.

### Quick deploy (user page)

```
cd ~/deltabox-paper-website
git init -b main
git add .
git commit -m "DeltaBox project page"
git remote add origin git@github.com:<username>/<username>.github.io.git
git push -u origin main
```

The page will be live at `https://<username>.github.io/` within a few
minutes (Pages settings &rarr; Source: `main` branch / root).

### Project-page deploy

If the target is a project page (`https://<username>.github.io/deltabox/`):

```
git init -b main
git add .
git commit -m "DeltaBox project page"
git remote add origin git@github.com:<username>/deltabox.git
git push -u origin main
```

Then on GitHub: **Settings &rarr; Pages &rarr; Source = `main` branch,
folder `/ (root)`**.

## Updating the citation

When the paper gets a venue / arXiv ID, edit the `<pre id="bibtex">`
block in `index.html` (e.g., add `eprint = {arXiv:XXXX.XXXXX}` or
replace `note = {Preprint}` with the actual conference).

## Updating figures

Source PDFs live in the paper repo. To refresh:

```
gs -sDEVICE=pngalpha -r144 -o assets/fig_cdf.png path/to/fig_cdf_only.pdf
```

PNG at 144 DPI keeps file size small while remaining sharp on retina.
