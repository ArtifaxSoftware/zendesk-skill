# Install Guide — Artifax Staff (Windows)

This guide walks Artifax staff through installing the Zendesk skill on a
Windows workstation, configuring authentication, and registering it with
Claude Code. It captures the platform-specific gotchas we hit when first
landing the skill on Windows in May 2026.

> **Install from the Artifax fork**, not PyPI or upstream. The fork
> (`ArtifaxSoftware/zendesk-skill`) carries three Windows compatibility
> fixes (commits [`58397c6`][c1], [`aa9e1b4`][c2], [`18610cc`][c3]) that
> aren't on PyPI. Installing from PyPI will crash on first run with
> `AttributeError: module 'os' has no attribute 'getuid'`.

[c1]: https://github.com/ArtifaxSoftware/zendesk-skill/commit/58397c6
[c2]: https://github.com/ArtifaxSoftware/zendesk-skill/commit/aa9e1b4
[c3]: https://github.com/ArtifaxSoftware/zendesk-skill/commit/18610cc

---

## 1. Prerequisites

You need on your workstation:

| Tool | Purpose | Check |
|---|---|---|
| **Python 3.12+** | Runtime for `zd-cli` | `python --version` |
| **Git** | Cloning + receiving updates | `git --version` |
| **winget** | Installing `uv` and `jq` | `winget --version` |

Python and Git are standard on Artifax dev images. `winget` ships with
Windows 11.

You also need a **Zendesk account** with permission to generate API tokens
(admin role, or someone who can generate one for you).

---

## 2. Install `uv` (Python package manager)

```powershell
winget install --id=astral-sh.uv -e
```

> **Important**: open a *new* PowerShell window after this step. The
> existing session won't see `uv` on PATH until it's restarted —
> environment variables set by winget aren't picked up by already-running
> shells.

Verify in the new window:

```powershell
uv --version
```

---

## 3. Install `zd-cli` from the Artifax fork

```powershell
uv tool install "git+https://github.com/ArtifaxSoftware/zendesk-skill"
```

If you've already installed an earlier version, replace `install` with
`install --force` to upgrade.

Verify:

```powershell
zd-cli --version
```

If `zd-cli` isn't found, see [Troubleshooting](#troubleshooting).

---

## 4. Authenticate to Zendesk

### 4a. Generate an API token

1. Open the Zendesk Admin Center.
2. Navigate to **Apps and integrations → APIs → Zendesk API**.
3. Make sure **Token access** is enabled.
4. Click **Add API token**, give it a useful description (e.g. `zd-cli on
   <hostname>`).
5. **Copy the token immediately** — Zendesk shows it only once.

You'll also need your Zendesk **subdomain** — the part before
`.zendesk.com` in your tenant URL (e.g. `artifax` if your URL is
`https://artifax.zendesk.com`).

### 4b. Log in

In your PowerShell terminal:

```powershell
zd-cli auth login
```

You'll be prompted for:

1. **Email** — your Artifax email
2. **API Token** — **the prompt hides what you type, including any pasted
   value.** You will see no asterisks, no cursor movement, no echo. This
   is intentional (same behaviour as `sudo` or `ssh` password prompts).
   Paste your token and press Enter — it *is* being captured.
3. **Subdomain** — e.g. `artifax`

If your terminal genuinely refuses to accept the hidden input (rare,
usually older PowerShell ISE or unusual SSH redirection), use this
non-interactive workaround instead:

```powershell
$env:ZD_TOKEN = Read-Host "Paste token" -AsSecureString | ConvertFrom-SecureString -AsPlainText
zd-cli auth login --email you@artifax.com --token $env:ZD_TOKEN --subdomain artifax
Remove-Item Env:\ZD_TOKEN
```

`Read-Host -AsSecureString` shows asterisks per keystroke, then we hand
the plaintext to `zd-cli` once and immediately wipe the environment
variable so it doesn't linger.

### 4c. Verify

```powershell
zd-cli auth status
zd-cli me
```

Both should return JSON including your Zendesk user record. If `me`
returns user details, your credentials are validated against the live
Zendesk API.

### 4d. Where credentials live

Your token is stored encrypted at rest under:

```
%USERPROFILE%\.config\zd-cli\secrets.json.enc
```

with the unencrypted config (email, subdomain) alongside it as
`config.json`. Both files are NTFS-ACL-locked to your user only — no
SYSTEM, Administrators, or other principals retain access. You can
verify with:

```powershell
icacls $env:USERPROFILE\.config\zd-cli\config.json
```

You should see a single line ending in `<DOMAIN>\<you>:(F)` and nothing
else.

---

## 5. (Optional) Install `jq`

`jq` is required by the `zd-cli query` sub-command, which extracts
specific fields from saved Zendesk responses. Without `jq`, the rest of
the skill still works — `query` just returns a friendly "jq is not
installed" message.

```powershell
winget install --id=jqlang.jq -e
```

Verify in a new PowerShell window:

```powershell
jq --version
```

---

## 6. Register the skill with Claude Code

Claude Code looks for skills under `%USERPROFILE%\.claude\skills\<name>\`.
We recommend a **directory junction** rather than a copy so `git pull`
updates flow through automatically.

### 6a. Clone the fork (if you haven't already)

```powershell
git clone https://github.com/ArtifaxSoftware/zendesk-skill C:\GitHub\zendesk-skill
```

### 6b. Create the junction

```powershell
New-Item -ItemType Directory -Path "$env:USERPROFILE\.claude\skills" -Force | Out-Null
cmd /c mklink /J "$env:USERPROFILE\.claude\skills\zendesk" "C:\GitHub\zendesk-skill"
```

Junctions (unlike symbolic links) don't require admin or developer mode.
After this, `%USERPROFILE%\.claude\skills\zendesk\SKILL.md` resolves to
the file in your clone.

### 6c. Restart Claude Code

Claude Code loads its skill list at session start. **Exit your current
Claude Code session and start a new one** for `/zendesk` to appear in the
skill list.

---

## 7. Updating later

Updates to the fork need to be pulled to the clone and reinstalled to the
`uv` tool environment. The junction picks up SKILL.md changes
automatically; the CLI tool does not.

```powershell
cd C:\GitHub\zendesk-skill
git pull
uv tool install --force "git+https://github.com/ArtifaxSoftware/zendesk-skill"
```

To check what version is currently installed:

```powershell
uv tool list
```

---

## Troubleshooting

### "uv is not recognized" after winget install

`winget` adds the new tool to your *user* PATH, but **already-running
shells don't see updates to PATH**. Open a new PowerShell window. If the
problem persists, reload PATH in your current shell:

```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
```

### "zd-cli is not recognized" after `uv tool install`

`uv` installs tool executables under `%USERPROFILE%\.local\bin`. If that
directory isn't on your PATH, run:

```powershell
uv tool update-shell
```

Then open a new PowerShell window.

### The token prompt looks frozen

It isn't — input is being hidden by design (see [Step 4b](#4b-log-in)).
Type/paste the token and press Enter. If genuinely stuck, use the
`Read-Host -AsSecureString` workaround in 4b.

### `AttributeError: module 'os' has no attribute 'getuid'`

You installed from PyPI or upstream instead of the Artifax fork.
Reinstall:

```powershell
uv tool install --force "git+https://github.com/ArtifaxSoftware/zendesk-skill"
```

### `/zendesk` doesn't appear in Claude Code's skill list

Skills load at session start. Exit and relaunch Claude Code. If still
missing, confirm the junction:

```powershell
Test-Path "$env:USERPROFILE\.claude\skills\zendesk\SKILL.md"
```

Should return `True`.

### Tests fail with file-permission assertions

You're on an older version of the fork. Pull and reinstall — commit
[`18610cc`][c3] introduced cross-platform owner-restriction. On Windows,
the test suite should be 98 pass / 0 fail with `jq` installed (96 pass /
2 skip without).

---

## Where to get help

- **Bugs in the skill itself**: file an issue on the
  [Artifax fork](https://github.com/ArtifaxSoftware/zendesk-skill/issues).
- **Zendesk API token / permissions issues**: contact your Zendesk
  administrator.
- **Claude Code skill discovery / harness questions**: see the official
  Claude Code documentation.
