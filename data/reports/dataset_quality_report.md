# Dataset Quality Report
## Summary
- Total trajectories: 36
- has_problem: 36 / 36 (100.0%)
- has_solution: 36 / 36 (100.0%)
- has_feedback: 36 / 36 (100.0%)
- has_linked_pr: 36 / 36 (100.0%)
- has_reward: 36 / 36 (100.0%)
- has_lesson: 36 / 36 (100.0%)

## Task Type Distribution
- bug_fix: 20
- feature: 7
- general: 6
- test_ci: 3

## Quality Flags
- missing_reproduction_steps: 26
- low_solution_pr_selection_confidence: 1

## Recommended Filters
- Strong trajectory: has_problem + has_solution + has_linked_pr
- High-value trajectory: strong trajectory + has_feedback
- Quarantine: missing_problem or missing_solution

## Interpretation
Use this report to decide whether the dataset is ready for Memory Agent and Bandit/RL runtime experiments. Do not train/retrieve from low-confidence trajectories without preserving their raw_refs.
