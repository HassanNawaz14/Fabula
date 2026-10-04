# Project Memory & Agent Operational Rules

## 1. Documentation Architecture
This project maintains two separate documentation directories under `docs/`:
- `docs/md/`: Markdown documentation (`DOCUMENTATION.md`) — designed for AI models, IDE previews, and fast contextual reading.
- `docs/latex/`: Academic LaTeX source and deliverables (`main.tex`, `main.pdf`, `.aux`, `.toc`) — designed strictly for the human user and academic submission.

---

## 2. STRICT PROHIBITION: Never Open or Read the `docs/latex/` Folder
- **RULE**: The AI assistant must **NEVER** open, view, grep, or inspect files inside `docs/latex/` (`docs/latex/main.tex`, etc.).
- **RATIONALE**: The LaTeX document contains the same technical content as `docs/md/DOCUMENTATION.md`, but carries heavy LaTeX syntactic overhead and boilerplate that wastes context tokens.
- **WORKING DOCUMENT**: Whenever the AI needs to read, update, or reference the project architecture and documentation, it must **ONLY** access `docs/md/DOCUMENTATION.md`.
- **LATEX COMPILATION**: Files in `docs/latex/` are strictly for the user's formal submission and should only be updated or compiled if the user explicitly gives a direct instruction to modify or recompile the LaTeX files.

---

## 3. General Project Context
- **System**: Small-scale Multi-Agent NPC Simulation with 5–10 autonomous characters in a discrete town environment.
- **Hybrid AI Architecture**:
  - *The Body (Classical AI)*: $A^*$ search (navigation), Genetic Algorithm (multi-objective schedule planning), MLP Neural Network (reflexive action classification), K-Means (unsupervised trajectory clustering).
  - *The Voice (LLM)*: Structured JSON prompt synthesis grounded strictly in private episodic memory to prevent state hallucinations.
- **Compute Budget**: 100% CPU executable; runs entirely on standard student laptop hardware without GPU or cloud API dependencies.
- **Repository Cleanliness**:
  - Root contains only `README.md`, `.gitignore`, `assets/`, and `docs/`.
  - LaTeX build logs (`*.log`) must always be removed after compiling.
