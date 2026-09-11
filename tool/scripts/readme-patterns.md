# High-Signal README Patterns

Use these patterns as modules, not as a universal table of contents. The best order follows the visitor's decision: understand, believe, try, then investigate.

## Opening contract

A strong first viewport usually contains:

- Identity: a clear project name and, when useful, a restrained logo or hero.
- Language: a compact edition switcher near the title without displacing the project's promise.
- Positioning: one concrete sentence describing what the project enables and why it is distinct.
- Trust: only relevant status, package, docs, license, community, paper, or demo links.
- Proof: a product state, terminal result, measurable comparison, or realistic output.
- Action: the shortest route to a demo, install, or successful command.

The elements can be reordered. A performance tool may lead with a benchmark; a visual application may lead with a screenshot; a library may lead with five lines of working code.

## Archetype modules

| Project archetype | Best early proof | Useful early modules | Common failure |
| --- | --- | --- | --- |
| Visual product | Hero screenshot, or a short recording when the interaction is the value | Value proposition, live demo, key workflows, quick start | Describing UI that visitors still cannot see |
| CLI or developer tool | Copyable terminal session and, if central, a reproducible benchmark | Highlights, install, common commands, compatibility | A long architecture preface before the first command |
| Library or API | Minimal working example with visible result | Install, core concepts, examples, API/docs link | Listing every API without showing the happy path |
| Model or research | Result visualization, honest benchmark, or architecture figure | News/status, model table, quick inference, training/evaluation, citation, limitations | Claims without datasets, settings, or comparison context |
| Infrastructure or platform | Dashboard, architecture, or deployment result | Capabilities, quick deploy, topology, integrations, security/operations | Treating the technology stack as the user value |
| Agent or skill | Concrete interaction or before/after workflow | Install/invoke, effect examples, method, boundaries, supported runtimes | Abstract promises with no realistic output |

For hybrids, choose one dominant opening and defer secondary audiences to later sections or dedicated docs.

## Proof patterns observed in successful repositories

- [colibri](https://github.com/JustVugg/colibri) pairs an unusually specific promise with real dashboard states, implementation status, measured numbers, and explicit caveats.
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) makes comparative performance the central proof, then moves directly into requirements, installation, and usage.
- [nuwa-skill](https://github.com/alchaincyf/nuwa-skill) uses a branded hero, concrete effect examples, multiple installation paths, and an honest-boundary section for an otherwise abstract agent skill.
- [Hermes Agent](https://github.com/NousResearch/hermes-agent) combines a banner, concise positioning, capability matrix, one-command install, and a route into deeper documentation.
- [Kronos](https://github.com/shiyu-coder/Kronos) uses live-demo and paper links, an architecture figure, model availability table, and runnable inference steps.
- [uv](https://github.com/astral-sh/uv) leads with a one-line category claim, quantitative benchmark visual, replacement story, and copyable terminal workflows.
- [n8n](https://github.com/n8n-io/n8n) puts a product screenshot next to a concise capability summary and an immediate local quick start.
- [Supabase](https://github.com/supabase/supabase) shows the dashboard, maps the platform's capabilities, and follows with a factual architecture view.
- [Excalidraw](https://github.com/excalidraw/excalidraw) treats the product showcase as the main proof, then keeps features and package quick start concise.
- [RustDesk](https://github.com/rustdesk/rustdesk) documents distinct product workflows with separate screenshots instead of relying on one generic hero.

Do not imitate their wording, badge count, or section order. Reuse the underlying choices: proof close to the claim, low-friction first use, progressive disclosure, and honest technical depth.

## Credibility rules

- Attach numbers to an environment, data set, method, or source. A benchmark without context is decoration.
- Distinguish released, experimental, planned, and unavailable capabilities.
- Keep important limitations near the affected feature or setup step.
- Prefer a few verified differentiators over exhaustive feature inventories.
- Use social proof only when it is attributable and useful to the intended audience.
- Link to deeper docs instead of turning the README into a complete manual.
- Keep a static proof frame for recorded workflows so the claim remains understandable without playback.
