---
name: codex-security-scan
description: Run a Codex Security scan. Run `codex-security scan --help` for usage details.
requires_bin: codex-security
command: codex-security scan
---

# codex-security scan

Run a Codex Security scan.

## Arguments

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `repository` | `string` | no | Repository root to scan (default: current directory). |

## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--config` | `string` |  | Load a trusted YAML/JSON file (default: CODEX_SECURITY_PROJECT_CONFIG, otherwise no file). |
| `--workflowId` | `string` |  | Reuse completed work in the named local findings workflow. |
| `--auth` | `string` | `auto` | Select ChatGPT, OPENAI_API_KEY/CODEX_API_KEY, or automatic authentication (default: auto). |
| `--verbose` | `boolean` | `false` | Print scan diagnostics to stderr. |
| `--safetyIdentifier` | `string` |  | Stable hashed end-user ID for this scan's model requests (1–64 characters). |
| `--path` | `array` |  | Scan only PATH; repeat for multiple repository-relative paths. |
| `--knowledgeBase` | `array` |  | Add security-context files or directories; repeat for multiple paths. |
| `--scanPromptFile` | `string` |  | Append scan instructions from FILE. |
| `--validationPromptFile` | `string` |  | Replace final validation with the workflow in FILE (not Deep). |
| `--postScanPromptFile` | `string` |  | Run FILE after each scan, including failures. |
| `--diff` | `string` |  | Scan committed Git changes from BASE to --head. |
| `--workingTree` | `boolean` | `false` | Scan staged and unstaged changes against --base. |
| `--head` | `string` |  | Git head ref for --diff (default: HEAD). |
| `--base` | `string` |  | Git base ref for --working-tree (default: HEAD). |
| `--mode` | `string` | `standard` | Scan mode (default: standard); deep supports repository and path targets. |
| `--workers` | `number` | `4` | Maximum concurrent deep-scan discovery workers. |
| `--subagents` | `number` | `3` | Subagents available to each deep-scan worker. Zero is valid. |
| `--stopAfterNoNew` | `number` | `4` | Stop after this many runs find no new issues. |
| `--maxDiscoveryRuns` | `number` | `40` | Maximum deep-scan discovery runs. |
| `--maxTimeHours` | `number` | `96` | Maximum deep-scan discovery hours (default: 96; maximum: 96). |
| `--model` | `string` |  | OpenAI model to use (default: gpt-5.6-sol). |
| `--effort` | `string` |  | Model reasoning effort (default: xhigh). |
| `--provider` | `string` | `openai` | Inference provider for scans. |
| `--outputDir` | `string` |  | Artifact directory outside the repository (default: Codex Security state; CODEX_SECURITY_STATE_DIR). |
| `--archiveExisting` | `boolean` | `false` | Archive existing results; requires --output-dir. |
| `--pluginPath` | `string` |  | Codex Security plugin directory or ZIP (default: bundled plugin). |
| `--python` | `string` |  | Python interpreter (default: PYTHON or automatic discovery). |
| `--codex` | `array` |  | Repeat TOML KEY=VALUE; e.g. model_reasoning_effort="high" or features.multi_agent_v2.max_concurrent_threads_per_session=4. |
| `--failOnSeverity` | `string` |  | Exit 1 for findings at or above LEVEL. |
| `--patch` | `boolean` | `false` | Patch and verify confirmed findings after the scan. |
| `--patchSeverity` | `string` |  | Patch findings at or above LEVEL; requires --patch. |
| `--createPr` | `boolean` | `false` | Create a draft GitHub pull request or GitLab merge request after verified patches. |
| `--maxCost` | `number` |  | Stop above AMOUNT in estimated USD; the dashboard offers increases near the limit. |
| `--showCost` | `boolean` | `false` | Show estimated USD cost; always shown when a cost limit is set. |
| `--headless` | `boolean` | `false` | Use plain text progress instead of the interactive dashboard. |
| `--dryRun` | `boolean` | `false` | Validate local scan inputs without starting a scan. |
| `--mock` | `boolean` | `false` | Save synthetic Standard scan findings without calling an LLM. |

## Output

Type: `unknown`

## Examples

```sh
codex-security scan .

codex-security scan . --config codex-security.yaml

codex-security scan . --model gpt-5.6-terra

codex-security scan . --model gpt-5.6-terra --effort high

codex-security scan . --path src

codex-security scan . --diff origin/main

codex-security scan . --codex features.multi_agent_v2.max_concurrent_threads_per_session=4
```

> Import existing findings without security analysis:
  codex-security scan import --csv findings.csv
  codex-security scan import --json findings.json
Use ./import to scan a repository named import. Confirm with the user before executing this destructive command.
