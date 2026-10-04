# Multi-Agent NPC Simulation: Hybrid Classical AI + LLM Brain

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![AI-Core](https://img.shields.io/badge/AI-Search%20%7C%20GA%20%7C%20ANN%20%7C%20Clustering-orange.svg)]()
[![LLM-Grounded](https://img.shields.io/badge/LLM-Grounded%20Dialogue-pink.svg)]()
[![Hardware-Friendly](https://img.shields.io/badge/Compute-100%25%20CPU%20Executable-green.svg)]()

> A small-scale multi-agent simulation where game characters (NPCs) perceive a dynamic town, maintain private memories and goals, make decisions using **Classical AI algorithms (Search, Genetic Algorithms, Neural Networks, Clustering)**, and engage in natural conversation through a **grounded Large Language Model (LLM)**.

---

## 📖 Full Technical Documentation
For the complete technical breakdown including mathematical formulations, research citations, prompt design, evaluation metrics, and ablation matrices:

- 📄 **Markdown Technical Docs (for AI / Reading)**: **[docs/md/DOCUMENTATION.md](docs/md/DOCUMENTATION.md)**
- 📕 **Academic PDF Report**: **[docs/latex/main.pdf](docs/latex/main.pdf)** (12-page compiled LaTeX report)
- 📐 **LaTeX Source (for User / TeX Compilation)**: **[docs/latex/main.tex](docs/latex/main.tex)**

---

## 🏛️ System Architecture

The simulation operates as a discrete tick-based loop, enforcing that physical reality is strictly managed by the game simulator:

![System Architecture: NPC Simulation Loop](assets/system_architecture.png)

- **Vector SVG**: [assets/system_architecture.svg](assets/system_architecture.svg)
- **High-Res PNG (2x)**: [assets/system_architecture.png](assets/system_architecture.png)

---

## 🎨 Clean Engineering Diagrams

All diagrams are designed with a minimalist light theme (simple boxes, clear arrows, zero clutter) and available in PNG and SVG formats:

| # | Diagram Title | Where Used | Formats |
|---|---|---|---|
| **01** | **[System Architecture: Simulation Loop](assets/system_architecture.png)** | Section 3: Overview of the 5-step perception-decision-action loop | [PNG](assets/system_architecture.png) • [SVG](assets/system_architecture.svg) |
| **02** | **[Decision Engine: Task & Tool Routing](assets/decision_engine_dispatch.png)** | Section 4: How tasks route to $A^*$, GA, MLP, and LLM | [PNG](assets/decision_engine_dispatch.png) • [SVG](assets/decision_engine_dispatch.svg) |
| **03** | **[Genetic Algorithm: Multi-Objective Flow](assets/genetic_algorithm_flow.png)** | Section 4.2: Chromosomes, fitness, and the 50-gen cycle | [PNG](assets/genetic_algorithm_flow.png) • [SVG](assets/genetic_algorithm_flow.svg) |
| **04** | **[Town Knowledge Separation & Diffusion](assets/town_knowledge_diffusion.png)** | Section 5: Sensory boundaries and social encounter timeline | [PNG](assets/town_knowledge_diffusion.png) • [SVG](assets/town_knowledge_diffusion.svg) |

---

## ⚙️ How It Works (The 5-Step Loop)

1. **World State**: The simulator maintains ground truth (town graph, item coordinates, NPC locations, clock).
2. **Perception Filter**: NPCs only see and hear events within their local sensory range (preventing unrealistic omniscience).
3. **Internal State**: Characters append observations to a **Memory Log** and track prioritized **Goals & Personality Traits**.
4. **Decision Engine**:
   - **$A^*$ Pathfinding**: Solves shortest-path physical navigation.
   - **Genetic Algorithm**: Solves multi-objective daily routes (balancing distance, danger, and clues).
   - **Neural Network (MLP)**: Predicts reflexive actions from state feature vectors.
   - **K-Means Clustering**: Analyzes emergent agent behaviors across runs.
   - **LLM Dialogue Brain**: Formulates natural in-character speech grounded strictly in the NPC's private memory.
5. **Action Execution**: Physical actions (`Move`, `Talk`, `Examine`, `PickUp`, `Wait`) are verified by the simulator, advancing time to the next tick.

---

## 🚀 8-Week Implementation Roadmap

```
Weeks 1–2: Environment & Simulator Core (Gymnasium Town Graph, Perception Filter, Memory Buffer)
Weeks 3–4: Classical AI Development (A* Pathfinding & Multi-Objective Genetic Algorithm)
Week 5:    LLM Dialogue & Interactive Web UI (FastAPI Backend + React / Vite Town Map)
Week 6:    Data Generation, MLP Training & K-Means Trajectory Clustering
Week 7:    Quantitative Evaluation, Ablation Studies & Fairness Testing
Week 8:    Final Technical Report, Charts, Demo Video & Code Packaging
```

> **Compute Requirements**: 100% CPU executable. Runs on standard student laptops without GPU clusters or cloud dependencies.
