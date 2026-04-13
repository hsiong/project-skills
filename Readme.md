
> + Globle dir: ~/.agents/skills
> + Repo dir: project/.agents/skills
> + 


A Codex skill is just a **folder** with a required `SKILL.md` file, plus optional helper files. The current official structure is: 

```
my-skill/
├─ SKILL.md              # required
├─ scripts/              # optional executable helpers
├─ references/           # optional docs/specs/examples
├─ assets/               # optional templates/resources
└─ agents/
   └─ openai.yaml        # optional metadata/dependencies
```

The minimum valid skill is even simpler: a folder with just `SKILL.md`, and that file must include YAML front matter with at least `name` and `description`. 

## 1) Smallest working skill

```
---
name: my-review-skill
description: Use this skill when reviewing Python code for readability, error handling, and obvious performance issues. Do not use it for frontend/UI design or infrastructure work.
---

When using this skill:

1. Read the target code before suggesting changes.
2. Check for:
   - obvious bugs
   - missing error handling
   - naming problems
   - unnecessary complexity
3. Prefer minimal changes over large rewrites.
4. When giving feedback:
   - explain the issue
   - show the fix
   - mention tradeoffs if any
```

That is enough for Codex to discover and use it. Codex first sees the skill metadata (`name`, `description`) for discovery, then loads the full `SKILL.md` only if it decides the skill is relevant. 

## 2) What each part does

### `SKILL.md`

This is the core of the skill.

It usually contains:

- YAML front matter
- when the skill should be used
- when it should **not** be used
- step-by-step workflow
- output format expectations
- guardrails

A good `description` is very important, because Codex can choose skills implicitly based on whether the task matches that description. 

A practical template:

```
---
name: skill-name
description: Use this skill when ____. Do not use it when ____.
---

# Purpose
What this skill helps with.

# When to use
- case A
- case B

# When not to use
- case X
- case Y

# Workflow
1. First do ...
2. Then check ...
3. Finally produce ...

# Rules
- Prefer ...
- Avoid ...
- Never ...

# Output
Return:
- summary
- risks
- next steps
```

## 3) Optional folders

### `scripts/`

Put helper scripts here when the skill needs repeatable automation.

Example:

```
my-skill/
├─ SKILL.md
└─ scripts/
   └─ validate.py
```

Then in `SKILL.md` you can instruct Codex to run it when needed, for example:

```
If the repository contains Python config files, run:

python scripts/validate.py
```

### `references/`

Put docs, examples, schemas, style guides, SQL snippets, API conventions here.

Example:

```
references/
├─ api-style.md
├─ db-schema.sql
└─ example-output.json
```

Use this for project-specific knowledge that the model would not reliably know on its own. Official guidance recommends being concise and only adding information Codex truly needs. 

### `assets/`

Use for templates or reusable files.

Example:

```
assets/
├─ pr_template.md
└─ changelog_template.md
```

### `agents/openai.yaml`

Optional metadata/dependency file. Official docs note Codex can also read optional metadata from `agents/openai.yaml`, and MCP dependencies can be declared there when a skill depends on external tools/services. 

## 4) Where to put the skill

For Codex, the documented locations are: 

- **Global/user skills**: `$HOME/.agents/skills`
- **Repo skills**: `.agents/skills` inside the repository

So for a repo-local skill:

```
your-project/
└─ .agents/
   └─ skills/
      └─ my-review-skill/
         └─ SKILL.md
```

For a global personal skill:

```
~/.agents/skills/my-review-skill/SKILL.md
```

## 5) How to create one quickly

Yes, **`$skill-creator` is the official built-in way** to start. The Codex docs explicitly recommend using it first. It asks what the skill does, when it should trigger, and whether it needs scripts or can stay instruction-only. 

So inside Codex, you can use:

```
$skill-creator
```

If you want to install curated or experimental skills from the OpenAI skills catalog, the official repo says to use `$skill-installer`. 

## 6) Example: a useful real skill

Suppose you want a skill for Java backend API review.

Folder:

```
.agents/skills/java-api-review/
├─ SKILL.md
├─ references/
│  └─ conventions.md
└─ scripts/
   └─ run_checks.sh
```

`SKILL.md`:

```
---
name: java-api-review
description: Use this skill when reviewing Java backend API code in Spring Boot projects. Focus on DTO design, controller/service layering, validation, exception handling, and API consistency. Do not use it for frontend code or infrastructure-only tasks.
---

# Purpose
Review Spring Boot API changes consistently.

# Workflow
1. Identify changed controller, service, DTO, and repository files.
2. Check API contract consistency:
   - request/response field naming
   - validation annotations
   - error response shape
3. Check layering:
   - controller should not contain business logic
   - service should not leak persistence details
4. Check DTOs:
   - clear field names
   - proper nullability/validation
   - serialization consistency
5. Run project checks if available:
   - bash scripts/run_checks.sh
6. Return:
   - findings
   - severity
   - suggested fixes

# Rules
- Prefer minimal, production-safe fixes.
- Do not recommend large refactors unless necessary.
- Show concrete code changes where possible.
```

## 7) What makes a skill good

Based on the official guidance, the important points are: 

- Keep it **narrowly scoped**
- Make `description` very explicit about **when to use** and **when not to use**
- Put only knowledge Codex is unlikely to know already
- Use `references/` and `scripts/` only when they add real value
- Prefer **short instructions + concrete examples** over long theory

## 8) One easy mistake

Do not write a vague description like:

```
description: Helps with coding tasks.
```

That is too broad, so Codex may not trigger it reliably.

Better:

```
description: Use this skill when editing Spring Boot REST APIs that include DTOs, request validation, and exception handling. Do not use it for frontend, SQL migration-only, or DevOps tasks.
```

That kind of description matches the documented trigger model much better. 

If you want, I can give you a **ready-to-use skill template** for your own case, such as:

- Spring Boot backend review
- Python data pipeline
- content generation compliance check
- OpenClaw / Codex workflow automation