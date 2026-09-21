---
name: codex-security-verify-fix
description: Verify existing security fixes without changing the repository. Run `codex-security verify-fix --help` for usage details.
requires_bin: codex-security
command: codex-security verify-fix
---

# codex-security verify-fix

Verify existing security fixes without changing the repository.

## Arguments

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `findings...` | `string` | no | Finding text, a file, or a saved finding identifier. |

## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--auth` | `string` | `auto` | Credential source: auto, chatgpt, or api-key. |
| `--effort` | `string` |  | Model reasoning effort (default: xhigh). |
| `--scan` | `string` |  | Verify open findings from a saved scan. |
| `--severity` | `string` |  | Verify saved findings at or above LEVEL. |
| `--linearIssue` | `array` |  | Linear issue identifier or URL; repeat for more issues. |
| `--linearProject` | `string` |  | Verify issues in this Linear project. |
| `--linearFilter` | `string` |  | JSON Linear issue filter for --linear-project. |
| `--linearApiKey` | `string` |  | Linear personal API key; defaults to CODEX_SECURITY_LINEAR_API_KEY. |
| `--codex` | `array` |  | Repeat TOML model="gpt-5.6-terra", model_reasoning_effort="high", or analytics.enabled=false. |

## Output

Type: `object`
