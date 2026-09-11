# Project Guide

Produce a comprehensive, source-backed guide for the specified project in Simplified Chinese by default, unless the user explicitly requests another language. Preserve code, commands, configuration keys, and other technical identifiers as written. Treat "no omissions" as a requirement to reconcile an explicit inventory, not a reason to claim certainty without evidence.

## Establish scope and evidence

- Use the requested project directory, or the current project when none is specified. Read its applicable instructions before inspection; ask for a path only if the intended project cannot be identified.
- Inventory all first-party modules, applications, packages, entry points, routes, commands, jobs, integrations, and deployment modes. Include optional, disabled, administrative, and experimental capabilities, labeling their status.
- Inspect permitted documentation, manifests and lockfiles, source, configuration examples and schemas, deployment and CI definitions, scripts, migrations, and relevant tests. Trace implementations and configuration consumers rather than relying on the README or a single keyword search. Exclude dependency and generated internals unless the project exposes or overrides their behavior.
- Respect file-access restrictions. Use allowed examples, bindings, schemas, or consuming code to recover configuration semantics; record remaining gaps. Replace sensitive values with placeholders.
- Maintain an evidence inventory linking each feature, configuration item, and run mode to its source path and symbol or line. Resolve contradictions against the checked-out implementation and label stale documentation, inferences, and unresolved behavior.

## Explain every feature

Group capabilities by module and user workflow. For each feature, explain its purpose, prerequisites and permissions, how to access or invoke it, inputs, outputs or state changes, a concrete usage example, and relevant limits or failure behavior. Cover supporting services and background work as well as the main interface. Distinguish implemented behavior from stubs, planned work, and test-only examples.

## Build the configuration reference

Enumerate project-specific settings from files, environment-variable reads, CLI flags, configuration bindings, defaults, feature flags, build and deployment definitions, and persisted or remote settings where present. Reconcile declarations with runtime consumers, including nested keys, aliases, and dynamically constructed names.

Use tables grouped by component. Record these fields for each setting:

- Exact key or flag, source location, and corresponding environment variable or alias.
- Meaning, type, units or format, required status, and default or behavior when omitted.
- Allowed values: list every member of a finite enum; otherwise specify the accepted range, pattern, schema, or open-ended value domain with representative examples. Distinguish enforced validation from recommendations, and mark unknown constraints instead of inventing them.
- A safe example, affected feature, dependencies or conflicts, environment-specific behavior, and whether changes require rebuilding, restarting, or take effect dynamically.

Explain loading order and override precedence from evidence, including profiles and secrets injection. Identify declared-but-unused and consumed-but-undocumented settings. For a delegated framework namespace, link its version-matched authoritative reference and enumerate project overrides; do not present framework defaults as project-specific settings.

## Explain setup and usage from zero

Provide an ordered path from a clean environment to a verified first result:

1. Supported operating systems, runtime and package-manager versions, hardware needs where relevant, external services, accounts, and credentials, distinguishing required from optional prerequisites.
2. Obtaining the project, selecting the relevant revision, installing dependencies using its lockfiles, and preparing local configuration with safe example values.
3. Provisioning dependencies, initializing or migrating storage, seeding required data, and building or generating assets in the correct order.
4. Starting components with the correct working directories, dependency order, profiles, and foreground or background behavior. Explain every supported run mode and its additional steps, including local, container, and production modes when present.
5. Checking readiness and completing the first end-to-end operation with expected observable results, then demonstrating the remaining feature groups and optional integrations.
6. Stopping services, handling persisted data, and diagnosing common failures through the relevant logs and checks. Explain upgrade or reset procedures when the project provides them, identifying destructive steps.

Derive commands from repository scripts and actual entry points. Name every placeholder and explain how to obtain its value.

## Verify and deliver

- Validate safe, feasible examples using the project's dependency environment. Explain commands with external side effects without executing them unless authorized. Label each run path as executed, statically checked, or unverified, with concrete blockers and next checks.
- Reconcile the guide against the evidence inventory: every discovered feature, setting, and run mode must be documented or explicitly marked unresolved. Check configuration coverage in both directions against declarations and consumers, and verify that setup examples provide their prerequisites and required settings.
- Deliver the guide with navigable sections for project scope, features, configuration, setup and usage, troubleshooting, and coverage gaps, citing source locations near the relevant claims. Follow any requested output location; otherwise answer in the conversation. For large projects, use a linked main guide and appendices under the existing documentation convention and report their paths instead of truncating the inventory. Do not rewrite the README unless requested.
- State the inspected revision or working-tree scope, what was verified, and any inaccessible sources or unresolved items. Claim completeness only within that explicitly checked scope.
