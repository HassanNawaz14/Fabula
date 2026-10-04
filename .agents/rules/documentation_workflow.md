# Rule: Documentation Workflow and File Access Restrictions

## Description
Enforces the separation between human-oriented LaTeX documents and AI-oriented Markdown documents within this workspace.

## Guidelines
1. **Never read `docs/latex/`**: Under no circumstances should the agent use `view_file`, `grep_search`, or other inspection tools on files within `docs/latex/` unless the user explicitly requests changes or compilation of the LaTeX report.
2. **Always use `docs/md/DOCUMENTATION.md`**: For all reading, architectural understanding, and documentation updates, use `docs/md/DOCUMENTATION.md`.
3. **Token Conservation**: Markdown is the designated context-efficient representation for AI interaction; LaTeX is the formal presentation deliverable for the user.
