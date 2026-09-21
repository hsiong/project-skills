---
name: code
description: 'Generate, complete, review, or refactor backend and frontend code (Java, Spring Boot, Feign, Python, React) adhering to strict engineering standards and common rules. Trigger when users ask to write or modify Java backend code, Feign clients, Python backend logic, or React components and UI pages. Do not trigger for ordinary git operations, issue tracking, or developer tooling.'
---

# Code Engineering & Style

Provide disciplined code generation, modification, and review across Java, Python, and React based on repository-established patterns and safety rules.

## Route the request

Identify the language, framework, and scope of the coding request to select the corresponding specification:

| Capability | Matching words and phrases | Instructions |
| --- | --- | --- |
| Java Backend Style | Java, Spring Boot, Java 后端, Controller, Service, Mapper, DTO, Result | [code-backend-java-style/SKILL.md](code-backend-java-style/SKILL.md) |
| Java Feign Integration | Feign, 接一个 Feign 接口, 补 decoder, 补 interceptor, HTTP client | [code-backend-java-feign-style/SKILL.md](code-backend-java-feign-style/SKILL.md) |
| Python Backend Style | Python, Python 后端, Python service, FastAPI, Flask, script | [code-backend-python-style/SKILL.md](code-backend-python-style/SKILL.md) |
| React Frontend Style | React, 前端, 组件, hook, signals, Tailwind, React 页面, UI 交互 | [code-front-react-style/SKILL.md](code-front-react-style/SKILL.md) |
| Common Standards | Implicitly enforced on all backend code generation and refactoring | [code-backend-common/SKILL.md](code-backend-common/SKILL.md) |

Read only the selected capability's instructions and supporting rules needed for the task.

## Shared execution rules

- **Minimal Diffs**: Make only the minimal necessary changes. Never refactor unrelated methods, reformat untouched code, or modify unrequested configurations.
- **English Comments**: All newly generated and modified code comments must default to English, explaining business intent rather than restating code literally.
- **Common Backend Standards**: All backend generation must satisfy the baseline constraints in [code-backend-common/SKILL.md](code-backend-common/SKILL.md).
