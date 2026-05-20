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

Claude Code looks for personal skills under
`%USERPROFILE%\.claude\skills\<name>\`. **The skill files must live in a
real directory** — Claude Code's skill scanner does not traverse Windows
directory junctions, so `mklink /J` will not work even though the files
appear visible. Use a copy.

### 6a. Clone the fork (if you haven't already)

```powershell
git clone https://github.com/ArtifaxSoftware/zendesk-skill C:\GitHub\zendesk-skill
```

### 6b. Copy SKILL.md and supporting files into the skills directory

```powershell
$dst = "$env:USERPROFILE\.claude\skills\zendesk"
New-Item -ItemType Directory -Path $dst -Force | Out-Null
Copy-Item C:\GitHub\zendesk-skill\SKILL.md      $dst
Copy-Item C:\GitHub\zendesk-skill\reference -Destination $dst -Recurse
```

Only `SKILL.md` and `reference/` need to be present — Claude Code does
not require `src/`, `tests/`, or the rest of the repo, and including
them only clutters the directory.

### 6c. Restart Claude Code

Claude Code loads its skill list at session start. **Exit your current
Claude Code session and start a new one** for `/zendesk` to appear in
the skill list. If `~/.claude/skills/` didn't exist before this step,
you may need a full Claude Code restart (not just a new session) for
the scanner to pick up the new top-level directory.

---

## 7. Use as an MCP server via Docker (Claude Desktop / Claude Code)

The Artifax fork ships a `Dockerfile` that packages `zendesk-mcp` as a
self-contained container. This lets you add the Zendesk skill as an MCP
server in **Claude Desktop** or **Claude Code** without installing Python
on the host at all — Docker handles the runtime.

### 7a. Prerequisites

- **Docker Desktop** installed and running.
- The image built from this repo (see below), or pulled from a shared
  registry if Artifax publishes one.

### 7b. Build the image locally

```powershell
cd C:\GitHub\zendesk-skill
docker build -t artifax/zendesk-mcp:dev .
```

The build takes 30–60 s on first run (downloading base images and deps);
subsequent builds are cached and take a few seconds.

Verify the image exists:

```powershell
docker images artifax/zendesk-mcp
```

### 7c. Wire it into Claude Desktop

Claude Desktop's MCP config lives at:

```
%APPDATA%\Claude\claude_desktop_config.json
```

Open or create that file and add the `zendesk` server under `mcpServers`:

```json
{
  "mcpServers": {
    "zendesk": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "ZENDESK_EMAIL",
        "-e", "ZENDESK_TOKEN",
        "-e", "ZENDESK_SUBDOMAIN",
        "artifax/zendesk-mcp:dev"
      ],
      "env": {
        "ZENDESK_EMAIL": "you@artifax.com",
        "ZENDESK_TOKEN": "your-api-token-here",
        "ZENDESK_SUBDOMAIN": "artifax"
      }
    }
  }
}
```

> **Security note:** The `env` block passes credentials to Docker's
> process environment (not visible in `docker ps` or process listings).
> The `claude_desktop_config.json` file itself should be kept private;
> do not commit it to source control or share it.

**Restart Claude Desktop** after editing the config. The Zendesk tools
(`zendesk_search`, `zendesk_get_ticket`, etc.) will then be available in
every chat session.

### 7d. Wire it into Claude Code

Claude Code MCP servers are configured in
`%USERPROFILE%\.claude\settings.json` (global) or `.claude/settings.json`
in a project root (project-scoped). Add the same block:

```json
{
  "mcpServers": {
    "zendesk": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-e", "ZENDESK_EMAIL",
        "-e", "ZENDESK_TOKEN",
        "-e", "ZENDESK_SUBDOMAIN",
        "artifax/zendesk-mcp:dev"
      ],
      "env": {
        "ZENDESK_EMAIL": "you@artifax.com",
        "ZENDESK_TOKEN": "your-api-token-here",
        "ZENDESK_SUBDOMAIN": "artifax"
      }
    }
  }
}
```

Start a new Claude Code session after saving. You can verify the server
is connected with:

```
/mcp
```

Which should list `zendesk` as a connected server with 26 tools.

### 7e. How it works

When Claude needs a Zendesk tool, it spawns the `docker run` command,
communicates with the container over **stdio** (the `-i` flag), and the
container exits cleanly when the session ends (`--rm`). No ports are
opened; no persistent container is left running.

---

## 8. Updating later

Pull the latest from the fork, then refresh whichever components you use:

```powershell
cd C:\GitHub\zendesk-skill
git pull

# Refresh the installed CLI binary (if using zd-cli / Claude Code skill)
uv tool install --force "git+https://github.com/ArtifaxSoftware/zendesk-skill"

# Refresh the skill files Claude Code sees
$dst = "$env:USERPROFILE\.claude\skills\zendesk"
Copy-Item C:\GitHub\zendesk-skill\SKILL.md      $dst -Force
Copy-Item C:\GitHub\zendesk-skill\reference -Destination $dst -Recurse -Force

# Rebuild the Docker image (if using the MCP server via Docker)
docker build -t artifax/zendesk-mcp:dev .

# Restart Claude Code / Claude Desktop so new versions are picked up
```

To check what CLI version is currently installed:

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

First, confirm the file is reachable:

```powershell
Test-Path "$env:USERPROFILE\.claude\skills\zendesk\SKILL.md"
```

Should return `True`. If yes but the skill still isn't discovered:

1. **Is the skill directory a junction?** Claude Code's skill scanner
   does **not** traverse Windows junctions, even though they appear
   transparent to most other tools. Check with:

   ```powershell
   (Get-Item "$env:USERPROFILE\.claude\skills\zendesk").LinkType
   ```

   If this returns `Junction`, that's the problem. Replace it with a
   real directory + file copies (see [Step 6b](#6b-copy-skillmd-and-supporting-files-into-the-skills-directory)):

   ```powershell
   $dst = "$env:USERPROFILE\.claude\skills\zendesk"
   Remove-Item $dst -Force
   New-Item -ItemType Directory -Path $dst -Force | Out-Null
   Copy-Item C:\GitHub\zendesk-skill\SKILL.md      $dst
   Copy-Item C:\GitHub\zendesk-skill\reference -Destination $dst -Recurse
   ```

2. **Did `~/.claude/skills/` exist when Claude Code started?** If the
   top-level skills directory was created mid-session, the scanner
   may not pick it up until the next *full* Claude Code restart (not
   just `/exit` and re-run). Try fully closing your terminal and
   reopening.

3. **Is the SKILL.md frontmatter valid YAML?** It must be a fenced
   block at the very top of the file, opening and closing with `---`,
   with at least `name:` and `description:` keys.

### Claude Desktop/Code shows "zendesk MCP server failed to start"

1. **Is Docker Desktop running?** The MCP client spawns `docker run`
   lazily — if Docker isn't running, the spawn fails silently. Start
   Docker Desktop and restart Claude.

2. **Does the image exist?** Run `docker images artifax/zendesk-mcp` — if
   the list is empty, build it (see [Step 7b](#7b-build-the-image-locally)).

3. **Are the env vars set in the config?** Open `claude_desktop_config.json`
   and check the `"env"` block has non-empty values for all three vars.

4. **Check Docker logs**: test the container manually:

   ```powershell
   echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0.0.1"}}}' | docker run --rm -i -e ZENDESK_EMAIL="you@artifax.com" -e ZENDESK_TOKEN="your-token" -e ZENDESK_SUBDOMAIN="artifax" artifax/zendesk-mcp:dev
   ```

   A valid JSON-RPC response with `"serverInfo"` means the server works —
   the issue is with the client config, not the image.

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
