# benj.office-hero

Office Hero web application.

## Development setup

```bash
# One-time setup (activates git hooks + installs deps)
bash scripts/setup-dev.sh        # Linux / macOS / Git Bash
.\scripts\setup-dev.ps1          # Windows PowerShell

# Run all quality gates locally
.\scripts\qa_gate.ps1            # Windows
pre-commit run --all-files       # any platform
```

## Quality gates

| Gate | Tool | When |
|------|------|------|
| Markdown lint | markdownlint | commit |
| Python format | black | commit |
| Python lint | ruff | commit |
| File hygiene | pre-commit-hooks | commit |
| Security scan | bandit | push |
| Unit tests | pytest | CI |
| Coverage | pytest-cov | CI |

## CI

GitHub Actions runs on every push and PR:

- **Lint** — pre-commit (black, ruff, markdownlint, file checks)
- **Security** — bandit static analysis
- **Test** — pytest with coverage report
