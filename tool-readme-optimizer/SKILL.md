---
name: tool-readme-optimizer
description: Create or overhaul repository READMEs as bilingual, evidence-led GitHub landing pages with project-specific positioning, quick starts, and verified visual proof. Use for requests like "rewrite the README," "make this look like a top GitHub project," "add a Chinese README," or "show the workflow in the README." Do not use for generic prose polishing, code review, implementation planning, or documentation pages unrelated to a repository README.
---

# README Optimizer

Turn a repository's real product experience into a README that helps a new visitor understand it, trust it, and try it quickly. Treat the README as a decision page, not a source-code report or a fixed essay template.

## Workflow

### 1. Establish the facts

- Read the current README, manifests, release metadata, user-facing entry points, CLI help, examples, tests, docs, and runnable demos. Inspect deeper implementation only to verify externally meaningful claims.
- Preserve applicable license, security, attribution, compatibility, and contribution information.
- Identify the primary audience, their first desired outcome, the shortest successful path, the project's maturity, and its strongest defensible proof.
- Build a private evidence map from each proposed claim to code, tests, docs, a reproducible run, or measured data. Remove unsupported superlatives and invented use cases.

### 2. Choose the story for this project

- Classify the project as a visual product, CLI/developer tool, library/API, model/research project, infrastructure/platform, agent/skill, or a justified hybrid.
- Read [references/readme-patterns.md](references/readme-patterns.md), then select only the modules that help this project's audience decide or act.
- Distill one precise promise and three to six differentiators. Lead with user-visible outcomes and proof; explain internals only when they establish trust or clarify a real design advantage.

### 3. Draft with visual proof

- Read [references/visual-playbook.md](references/visual-playbook.md) and inventory existing visual assets before creating new ones.
- Sketch the README's reading order and mark the claims that need visual proof before capturing anything. Choose each asset for a known placement instead of producing a generic gallery up front.
- For a runnable visual product, launch it with safe demo data and capture the smallest set of real states or interactions that proves the core experience. Use an available browser tool or [scripts/capture_readme.py](scripts/capture_readme.py).
- Keep a reproducible capture configuration for every committed product screenshot or recording. Include a product-specific ready selector and computed-style checks for the primary surface; never rely on a fixed delay alone.
- Record a short interaction when the value depends on motion, sequence, direct manipulation, live feedback, or a state transition that screenshots would obscure. Use a screenshot for a stable result and pair every recording with a useful static frame.
- For a CLI, library, model, or infrastructure project, prefer the visual evidence that best fits the claim: a terminal transcript, rendered result, benchmark chart, architecture diagram, model table, or workflow trace.
- Never fabricate a product screenshot. Generated artwork may serve as clearly decorative branding, but not as evidence of implemented behavior. If the project cannot be run, reuse verified assets or create a fact-based diagram and report the missing capture rather than disguising it.
- Inspect every captured bitmap at full resolution and compare it with the live product before embedding it. Treat missing styles, fonts, images, data, or partially rendered states as capture failures even when the capture command exits successfully.
- Store durable assets under the repository's existing documentation convention, or `docs/images/readme/` when none exists. Use descriptive names, useful alt text, and captions that state what the image proves.
- Work section by section: draft the claim and its proof slot, acquire the missing asset, then revise the wording to match what the asset actually demonstrates. Do not complete all captures before writing or force final copy around an unverified capture plan.

### 4. Refine the decision order

Build the opening viewport from the strongest available elements:

1. Recognizable project name or restrained brand asset.
2. A one-sentence promise naming the product, audience or task, and meaningful advantage.
3. A few relevant trust links or badges.
4. A primary action such as Try, Install, View demo, or Read docs.
5. Immediate proof: a real screenshot, focused recording, short terminal session, output example, or benchmark.

After the opening, arrange project-specific modules such as highlights, quick start, examples, performance, architecture, compatibility, configuration, limitations, roadmap/status, support, contributing, citation, and license. Put the first successful run early, move exhaustive reference material into linked docs, and keep each section centered on one reader question.

Use the repository's audience language. Keep commands copyable, examples concrete, headings scannable, and claims proportional to evidence. Do not turn internal class names, file inventories, or every implemented feature into the story.

### 5. Publish and verify both editions

- Write the root `README.md` in English and a complete Simplified Chinese edition at `docs/zh-CN/README-cn.md`; do not reduce the Chinese edition to a summary.
- Put `English | [简体中文](docs/zh-CN/README-cn.md)` near the top of the English edition and `[English](../../README.md) | 简体中文` in the corresponding position of the Chinese edition.
- Keep their section order, claims, commands, warnings, status labels, and visuals equivalent. Translate reader-facing prose, alt text, and captions naturally; preserve code, identifiers, filenames, environment variables, package names, and URLs.
- Resolve every local link, image, recording, and anchor from each file's location. Update both editions whenever the narrative or evidence changes.
- Run the documented quick start or the smallest safe validation that verifies it. Render both files and check their paths, code fences, dark/light presentation where relevant, and GitHub-compatible markup.
- Play every recording from the committed or hosted target, verify that it shows only the intended flow, and confirm that its poster or static fallback communicates the same outcome without motion.
- Review the rendered reading order and `git diff`. Remove duplicated claims, decorative clutter, stale instructions, and sections that delay the first useful action.
- Finish with a concise summary of both editions, created or reused visuals, checks run, and any claim or visual that could not be verified.
