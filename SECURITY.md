# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | Yes                |

## Reporting a Vulnerability

If you discover a security vulnerability in kicad-mcp, please report it responsibly:

1. **Do not** open a public GitHub issue for security vulnerabilities
2. Email the maintainers or use [GitHub Security Advisories](https://github.com/laurigates/kicad-mcp/security/advisories/new) to report privately
3. Include steps to reproduce the vulnerability
4. Allow reasonable time for a fix before public disclosure

## Security Measures

- **Static analysis**: Bandit scans run in CI on every push
- **Secret detection**: TruffleHog pre-commit hook prevents accidental secret commits
- **Dependency monitoring**: Dependabot monitors for vulnerable dependencies
- **Input validation**: File paths are validated to prevent path traversal
- **Secure XML parsing**: Uses `defusedxml` to prevent XML-based attacks
