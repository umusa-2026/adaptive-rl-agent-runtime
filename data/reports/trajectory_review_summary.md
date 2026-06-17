# Trajectory Review Summary

| Issue | Score | Grade | Decision | Selected PR | Flags | Title |
|---:|---:|---|---|---:|---|---|
| 13969 | 96 | A | USE_FOR_RUNTIME_LEARNING | 14000 |  | [Bug]: tavily settings gets reset when you go from advanced to basic |
| 13971 | 94 | A | USE_FOR_RUNTIME_LEARNING | 13978 |  | [Bug]: Basic and Advanced for "Verification" is the same |
| 13972 | 80 | A | USE_FOR_RUNTIME_LEARNING | 13976 | missing_reproduction_steps | Remove shared conversations search endpoint |
| 13975 | 94 | A | USE_FOR_RUNTIME_LEARNING | 14033 |  | [Bug]: MCP server settings are lost when you save LLM settings |
| 13982 | 91 | A | USE_FOR_RUNTIME_LEARNING | 13996 |  | [Bug]: MCP settings is not aligned properly to the left |
| 13984 | 91 | A | USE_FOR_RUNTIME_LEARNING | 14184 |  | [Bug]: Cannot get GPT 5.4 with OpenAI provider to work |
| 13986 | 84 | A | USE_FOR_RUNTIME_LEARNING | 14013 | missing_reproduction_steps | CLOUD - Hide the All button on the LLM page |
| 13987 | 84 | A | USE_FOR_RUNTIME_LEARNING | 13988 | missing_reproduction_steps | VS Code tab shows "Bad Gateway" — stale URL after new runtime provisioned on conversation resume |
| 13991 | 82 | A | USE_FOR_RUNTIME_LEARNING | 13994 | missing_reproduction_steps | Render ACPToolCallEvent in the conversation viewer |
| 13999 | 73 | B | USE_WITH_CAUTION | 14321 | missing_reproduction_steps | Plumb user LLM credentials into ACP subprocess env (today only OH_AGENT_SERVER_ENV works) |
| 14007 | 79 | B | USE_WITH_CAUTION | 14009 | missing_reproduction_steps | Add secrets field to AppConversationStartRequest for direct API secret passing |
| 14010 | 33 | D | QUARANTINE | None | missing_linked_pr, missing_selected_solution_pr, missing_solution_summary, missing_reproduction_steps | Integration Suggestion: Enabling Agent-to-Agent Commerce via Merxex |
| 14023 | 76 | B | USE_WITH_CAUTION | 14026 | missing_reproduction_steps | refactor(server): extract legacy HTTP router registration from app.py |
| 14039 | 72 | B | USE_WITH_CAUTION | 2999 | missing_reproduction_steps, low_solution_pr_selection_confidence | [Bug]: "accumulated_token_usage" data in the conversation/id/events/search V1 API response is returning an empty dict |
| 14095 | 82 | A | USE_FOR_RUNTIME_LEARNING | 14233 | missing_reproduction_steps | Implement Bitbucket Data Center webhook handler for @OpenHands resolver |
| 14096 | 96 | A | USE_FOR_RUNTIME_LEARNING | 14097 |  | Integrations page is blank when GITHUB_APP_SLUG is not set (Replicated/self-hosted) |
| 14100 | 82 | A | USE_FOR_RUNTIME_LEARNING | 14102 | missing_reproduction_steps | Auto-titling broken for webhook-created conversations (automation runs) |
| 14107 | 80 | A | USE_FOR_RUNTIME_LEARNING | 14110 | missing_reproduction_steps | GitlabV1CallbackProcessor not registered for deserialization in webhook router |
| 14153 | 96 | A | USE_FOR_RUNTIME_LEARNING | 14155 |  | [Bug]: Cannot edit or remove integrations tokens from local GUI |
| 14167 | 79 | B | USE_WITH_CAUTION | 14171 | missing_reproduction_steps | feat: inject user secrets into ACP agent subprocess env |
| 14183 | 73 | B | USE_WITH_CAUTION | 14187 | missing_reproduction_steps | feat(frontend): ACP agent selection UI — sidebar item, settings pages, dynamic nav |
| 14220 | 24 | D | QUARANTINE | None | missing_linked_pr, missing_selected_solution_pr, missing_solution_summary, missing_feedback, missing_reproduction_steps | Automatically add OPENHANDS_API_KEY as a secret to every user's settings |
| 14222 | 82 | A | USE_FOR_RUNTIME_LEARNING | 14401 | missing_reproduction_steps | feat(acp): minimal generic ACP agent UI (no per-provider scaffolding) |
| 14240 | 33 | D | QUARANTINE | None | missing_linked_pr, missing_selected_solution_pr, missing_solution_summary, missing_reproduction_steps | Starlog published a deep-dive on OpenHands/OpenHands |
| 14244 | 76 | B | USE_WITH_CAUTION | 14246 | missing_reproduction_steps | Remove 'ACP ·' prefix from tool call messages in chat UI |
| 14245 | 76 | B | USE_WITH_CAUTION | 14247 | missing_reproduction_steps | ACP tool calls flash empty state before populating with real values |
| 14248 | 91 | A | USE_FOR_RUNTIME_LEARNING | 14286 |  | [Bug] hardcoded English strings in settings not using translation system (i18n) |
| 14268 | 77 | B | USE_WITH_CAUTION | 14269 | missing_reproduction_steps | GCS storage.Client() created per-request causes connection pool exhaustion under load |
| 14272 | 24 | D | QUARANTINE | None | missing_linked_pr, missing_selected_solution_pr, missing_solution_summary, missing_feedback, missing_reproduction_steps | Integration Proposal: CAJAL Scientific Paper Generator for OpenHands |
| 14275 | 24 | D | QUARANTINE | None | missing_linked_pr, missing_selected_solution_pr, missing_solution_summary, missing_feedback, missing_reproduction_steps | [Bug] Runtime container fails to start - micromamba not found in runtime:latest |
| 14276 | 24 | D | QUARANTINE | None | missing_linked_pr, missing_selected_solution_pr, missing_solution_summary, missing_feedback, missing_reproduction_steps | [Bug] Runtime container fails to start - micromamba not found in runtime:latest |
| 14280 | 24 | D | QUARANTINE | None | missing_linked_pr, missing_selected_solution_pr, missing_solution_summary, missing_feedback, missing_reproduction_steps | 📝 Integration Proposal: CAJAL — Local Scientific Paper Generation for OpenHands |
| 14293 | 24 | D | QUARANTINE | None | missing_linked_pr, missing_selected_solution_pr, missing_solution_summary, missing_feedback, missing_reproduction_steps | 📝 Integration Proposal: CAJAL — Scientific Paper Agent |
| 14294 | 84 | A | USE_FOR_RUNTIME_LEARNING | 14297 | missing_reproduction_steps | OpenHands provider should appear first in providers lists |
| 14317 | 24 | D | QUARANTINE | None | missing_linked_pr, missing_selected_solution_pr, missing_solution_summary, missing_feedback, missing_reproduction_steps | Claude Max authentication for Claude Code ACP agent (cloud) |
| 14322 | 82 | A | USE_FOR_RUNTIME_LEARNING | 14401 | missing_reproduction_steps | fix(settings): switching agent_kind leaks stale fields across discriminated union types |
| 14325 | 80 | A | USE_FOR_RUNTIME_LEARNING | 14326 | missing_reproduction_steps | fix: org settings PATCH 500 error for installs upgrading from legacy agent_kind='llm' DB rows |
| 14349 | 38 | D | QUARANTINE | None | missing_linked_pr, missing_selected_solution_pr, missing_solution_summary, missing_feedback | [Bug]: cli shows ascii format of unicode, not readable |
| 14364 | 33 | D | QUARANTINE | None | missing_linked_pr, missing_selected_solution_pr, missing_solution_summary, missing_reproduction_steps | [Feature]: Allow independent control of slots (-ns) and parallelism (-np) |
| 14370 | 73 | B | USE_WITH_CAUTION | 14453 | missing_reproduction_steps | ACP settings: preserve LLM/condenser/MCP config across OpenHands ↔ ACP toggles |
| 14376 | 74 | B | USE_WITH_CAUTION | 14380 | missing_reproduction_steps | Bug: `<Trans>` drops space before `<cmd>` in action/observation titles (visible on ACP, latent on OpenHands) |
| 14405 | 77 | B | USE_WITH_CAUTION | 14406 | missing_reproduction_steps | Enable LLM Profiles for SaaS (Org-Level Storage) |
| 14417 | 84 | A | USE_FOR_RUNTIME_LEARNING | 14418 | missing_reproduction_steps | Sub-agent delegation task tool reports no registered sub-agents |
| 14419 | 100 | A | USE_FOR_RUNTIME_LEARNING | 14437 |  | [Bug]: OpenRouter configuration still appears to consume OpenHands credits |
| 14455 | 49 | D | QUARANTINE | None | missing_linked_pr, missing_selected_solution_pr, missing_solution_summary | [Bug]: Cloud agent 500: Sandbox failed to start within 120s: 1hCAH2KVIA705fk2ZO3twE |
| 14480 | 78 | B | USE_WITH_CAUTION | 14483 | missing_reproduction_steps | Slack resolver: missing critic API key causes generic "unexpected error" instead of user-friendly message |
| 14501 | 19 | D | QUARANTINE | None | missing_linked_pr, missing_selected_solution_pr, missing_solution_summary, missing_feedback, missing_reproduction_steps | [DELETED] |
| 14556 | 82 | A | USE_FOR_RUNTIME_LEARNING | 14557 | missing_reproduction_steps | Remove null wildcard matching from event callback execution |
| 14591 | 91 | A | USE_FOR_RUNTIME_LEARNING | 14593 |  | [Bug]: Last version of package miss standard-aifc in pyproject.toml |
| 14602 | 18 | D | QUARANTINE | None | missing_issue_body, missing_linked_pr, missing_selected_solution_pr, missing_solution_summary, missing_feedback, missing_reproduction_steps | test |
