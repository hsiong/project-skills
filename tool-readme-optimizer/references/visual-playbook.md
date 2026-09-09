# README Visual Playbook

Use visuals to demonstrate a claim that text cannot prove as quickly. Every image should answer a specific visitor question.

## 1. Inventory before capture

Search the repository for existing images, recordings, diagrams, demo fixtures, seeded accounts, storybooks, and end-to-end tests. Verify that reused assets still match the current product.

Useful discovery commands:

```bash
rg --files | rg '\.(png|jpe?g|webp|gif|svg|mp4|webm)$'
rg -n 'storybook|playwright|cypress|fixture|seed|demo' .
```

## 2. Make a capture plan

For each proposed visual, define:

| Field | Question |
| --- | --- |
| Claim | What statement will this prove? |
| Surface | Which page, command, result, or diagram contains the proof? |
| State | What safe data and interaction state make it understandable? |
| Format | Screenshot, recording, terminal block, chart, SVG, or Mermaid? |
| Placement | Where does the reader need this proof? |

Prefer one strong hero plus two to four focused proof visuals. Use more only when distinct workflows genuinely need them.

Use a screenshot when one stable state proves the claim. Use a recording only when timing or interaction carries information, such as drag-and-drop, live generation, progress, collaboration, or a multi-step transition. Keep the flow focused, typically 5–15 seconds, and identify the static frame that will work as its fallback.

Create the plan from a provisional README outline, then capture on demand while drafting. If the copy exposes a missing proof point, add that asset and revise the claim after inspecting the result; do not take every possible screenshot before the narrative is known.

## 3. Capture a web product

Start the application using its documented package manager and lockfile. Use deterministic fixtures or demo data, remove tokens and personal information, and wait until fonts, charts, and asynchronous content are stable.

When no browser capture tool is available, create a JSON file and run the bundled script. It supports deterministic screenshots and recorded interaction sequences:

```json
{
  "base_url": "http://127.0.0.1:3000",
  "output_dir": "docs/images/readme",
  "defaults": {
    "viewport": {"width": 1440, "height": 900},
    "color_scheme": "dark",
    "wait_ms": 500,
    "routes": [
      {
        "url": "**/api/demo",
        "method": "GET",
        "json": {"items": [{"name": "Safe demo"}]}
      }
    ],
    "style_checks": [
      {"selector": ".dashboard-grid", "property": "display", "equals": "grid"},
      {"selector": "[data-ready='true']", "property": "opacity", "equals": "1"}
    ]
  },
  "captures": [
    {
      "kind": "screenshot",
      "name": "overview.png",
      "path": "/dashboard?demo=1",
      "wait_for": "[data-ready='true']",
      "hide": ["[data-private]", ".dev-toolbar"]
    },
    {
      "kind": "recording",
      "name": "workflow.webm",
      "poster": "workflow.png",
      "gif": "workflow.gif",
      "path": "/workflows/example",
      "wait_for": "[data-ready='true']",
      "hide": ["[data-private]", ".dev-toolbar"],
      "actions": [
        {"action": "click", "selector": "[data-demo='new-step']"},
        {
          "action": "drag_to",
          "selector": "[data-step='source']",
          "target": "[data-canvas]"
        },
        {"action": "wait_for", "selector": "[data-save-state='saved']"},
        {"action": "wait", "ms": 800}
      ],
      "gif_options": {"fps": 12, "width": 960}
    }
  ]
}
```

```bash
python -m pip install -r /path/to/tool-readme-optimizer/requirements.txt
python -m playwright install chromium ffmpeg
python /path/to/tool-readme-optimizer/scripts/capture_readme.py readme-captures.json
```

The script accepts `click`, `fill`, `press`, `hover`, `check`, `uncheck`, `select_option`, `drag_to`, `scroll_into_view`, `wait_for`, and timed `wait` actions. Use `routes` to fulfill deterministic API responses with safe demo data before navigation; each route needs a Playwright URL pattern plus `json` or `body`, and may specify `method`, `status`, `headers`, and `content_type`. The legacy `shots` field remains supported, but legacy configs must satisfy the current validation gates. Before writing an asset, the script waits for network idle, linked stylesheets, fonts, DOM images, and computed-style image resources; a failed visual resource aborts the capture. Set `wait_for_network_idle`, `wait_for_stylesheets`, `wait_for_fonts`, `wait_for_images`, or `wait_for_background_images` to `false` only when the excluded resource is proven irrelevant to the intended frame.

Add `style_checks` for at least two distinctive computed styles on the primary product surface so a missing or stale stylesheet fails loudly. Each check needs `selector`, `property`, and exactly one of `equals`, `not_equals`, or `contains`. The script enforces two checks by default. Set `minimum_style_checks` lower only for a canvas, WebGL view, or another surface where computed CSS cannot establish visual readiness, and document the alternative verification in the handoff.

The script's Python dependencies are declared in `requirements.txt`; install them in an isolated environment. It also needs a Chromium browser; set a top-level `browser_channel` such as `chrome` to use an installed browser channel. Recordings need Playwright's FFmpeg component, while GIF generation needs an FFmpeg executable on `PATH`; `gif_options` can control `fps`, `width`, `colors`, `start_ms`, and `duration_ms`. Keep the capture config beside the documentation workflow whenever a generated visual is committed, so maintainers can reproduce and revalidate it.

After every capture, inspect the actual bitmap at full resolution with an image-viewing tool before embedding it. Compare the captured state with the live page and verify the intended layout, typography, theme, loaded images, meaningful data, crop, and absence of private information. A successful command or existing PNG is not visual verification. Delete or replace a capture that looks partially styled, blank, stale, or materially different from the running product.

Use a consistent viewport and color scheme across a series. Capture a mobile viewport only when responsive behavior is part of the value. Crop to the meaningful surface, remove setup and idle time from recordings, avoid transient toasts unless they are the proof, and never stage functionality the application does not implement.

## 4. Choose non-UI evidence

- CLI: use a short real terminal transcript in a code block; use a recording only when interaction or progress is important.
- Library/API: show the smallest input and returned or rendered result together.
- Performance project: produce a labeled chart or table from checked-in benchmark data and state the environment.
- Model/research project: show representative output, comparison, architecture, or evaluation with provenance.
- Infrastructure: use a diagram for relationships and a screenshot for operational experience; do not make one substitute for the other.

Prefer Mermaid for simple GitHub-native flows and SVG for controlled diagrams. Derive nodes and edges from verified repository behavior.

## 5. Prepare and embed assets

- Use stable repository-relative paths and descriptive lowercase filenames.
- Prefer PNG for sharp UI/text, WebP for smaller rich images, SVG for diagrams, and a short WebM master plus an optimized GIF only when motion carries information.
- Use the GIF for repository-relative inline motion. When video quality matters more, link its poster to the WebM or to a verified hosted video; verify the target renderer instead of assuming raw video HTML will work.
- Keep recordings silent, free of personal data and credentials, readable at the embedded size, and understandable from their alt text, caption, and poster without requiring motion.
- Avoid oversized canvases and assets that take longer to load than the surrounding README. Optimize a copy rather than degrading the source asset.
- Write alt text that conveys the demonstrated state, not `screenshot`. Add a short caption when the takeaway is not obvious.
- Use a `<picture>` element only when separate light and dark assets materially improve readability.

After embedding, render both `README.md` and `docs/zh-CN/README-cn.md` in a GitHub-compatible preview. Verify each file's local paths, playback or linked-video behavior, dimensions, translated alt text and captions, and layout in both narrow and wide views.
