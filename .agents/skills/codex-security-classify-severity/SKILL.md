---
name: codex-security-classify-severity
description: Classify saved findings using an optional rubric and save a separate severity assessment. Run `codex-security classify-severity --help` for usage details.
requires_bin: codex-security
command: codex-security classify-severity
---

# codex-security classify-severity

Classify saved findings using an optional rubric and save a separate severity assessment.

## Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--reprocess` | `boolean` | `false` | Reclassify selected findings even when a matching assessment is saved. |
| `--scan` | `string` |  | Saved scan ID, unique prefix, or latest. |
| `--scanDir` | `string` |  | External completed scan directory. |
| `--rubric` | `string` |  | Classification policy document; omit to inherit existing severity without a model call. |
| `--knowledgeBase` | `array` |  | Supporting security context; repeat for more files or directories. |
| `--findingId` | `array` |  | Classify only this finding ID; repeat to select deduplicated findings. |
| `--model` | `string` |  | Model for rubric classification. |
| `--effort` | `string` |  | Classification reasoning effort (default: medium). |

## Output

Type: `object`

> Confirm with the user before executing this destructive command.
