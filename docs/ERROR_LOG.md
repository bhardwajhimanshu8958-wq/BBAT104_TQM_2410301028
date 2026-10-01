# Software Quality & Defect Error Log

| Error ID | Date | Phase / Commit | Symptom | Root Cause | Fix / Mitigation | Prevention Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **ERR-001** | 2026-10-01 | Phase 2 / Commit 12 | `git push` times out with `Failed to connect to github.com:443` | Campus/local network firewall or proxy blocking outbound TCP port 443 to GitHub IP address (20.207.73.82) | Maintain clean linear Git commit history locally; push once connected to mobile hotspot or VPN, or configure HTTP proxy | Test upstream network connectivity during preflight check; document offline commit protocol |

## Upstream Git Push Status & Instructions

- **Local Branch**: `main` (clean linear commits, zero force push / amend)
- **Current Remote**: `https://github.com/bhardwajhimanshu8958-wq/BBAT104_TQM_2410301028.git`
- **Diagnosed Issue**: Outbound TCP port 443 to `github.com` timed out (`PingSucceeded: False`, `TcpTestSucceeded: False`) on the current Wi-Fi network interface (`10.163.252.116`).
- **Immediate User Action to Push**:
  1. Switch to a mobile hotspot or connect through a VPN / authorized institutional proxy.
  2. Run `git push -u origin main` in the terminal to upload all commits in one step.
