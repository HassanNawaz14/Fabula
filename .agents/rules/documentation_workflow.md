# Rule: Documentation Workflow and File Access Restrictions

## Description
Enforces the separation between human-oriented LaTeX documents and AI-oriented Markdown documents within this workspace, and the precedence of the project's sources of truth.

## Guidelines
1. **Never read `docs/latex/`**: Under no circumstances should the agent use `view_file`, `grep_search`, or other inspection tools on files within `docs/latex/` unless the user explicitly requests changes or compilation of the LaTeX report (it still reflects the previous, pre-sync edition until regenerated).
2. **Markdown for working context**: For all reading, architectural understanding, and documentation updates, use `docs/md/DOCUMENTATION.md`.
3. **Truth files decide**: For any product decision (scope, features, architecture choices), `docs/features.md` and `docs/FABULA_DEVPLAN_SOURCE.md` are the sole sources of truth; the generated plan lives in `docs/dev_plan/`. On conflict with `README.md`, `DOCUMENTATION.md`, or `assets/`, the truth files win.
4. **Token Conservation**: Markdown is the designated context-efficient representation for AI interaction; LaTeX is the formal presentation deliverable for the user.
