# Security Policy

## Scope

`steam-achievement-unlocker-offline` is a **purely offline** tool. It reads
and writes local Steam files under a user-specified Steam install path. It
makes no network requests. Any issue that involves network egress, remote
code execution, or privilege escalation beyond the user's own profile is
in scope and treated as high severity.

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.4.x   | yes       |
| < 0.4   | no        |

## Reporting

Open a private security advisory on the GitHub repo. Include:

- Steam client version and build
- Windows version
- The exact command line used
- A copy of `data/backups/` timestamps around the run
- Redacted `steam_offline_state.json` if relevant

Do not attach raw `UserGameStats_*.bin` files to a public issue — they
contain your SteamID64 and playtime.

## Known non-issues

- "It didn't unlock achievements in a game I don't own." By design.
- "Steam reset my achievements." Steam reconciles local cache against the
  cloud on next online launch. That's Steam's behavior, not ours. Use
  the tool with Steam closed and don't launch the game online until you've
  verified what you wanted to verify.
- "Antivirus flagged the build." PyInstaller one-file builds routinely
  trip heuristics. Build from source if you care.

## Threat model

The attacker is a malicious schema file or a tampered `UserGameStats` blob
you feed the tool. Mitigations: strict binary parsing with length checks,
no `eval`, no `pickle`, no `subprocess` with shell=True, and a hard cap on
schema entry count.