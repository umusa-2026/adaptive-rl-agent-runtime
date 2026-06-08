# Architecture

```text
Query -> Memory Agent -> Planner/Policy -> Reflection -> Evaluator -> Trajectory Logger -> Policy Learning
```

The project separates foundation model intelligence from runtime intelligence. Runtime intelligence includes memory retrieval, reflection, evaluation, reward design, and policy learning.
