# SEParser Mac Setup Guide

This file is for a Claude agent to use when helping the user install SEParser on a Mac. Walk through each step conversationally, confirm completion before moving to the next step, and handle errors as they come up. The user is not technical — avoid jargon, explain what each step does in plain language.

---

## What This Tool Does

SEParser lets you paste a StreetEasy listing URL into this chat and get back a structured summary of the property — price, beds, baths, building details, price history, and more. Once installed, you just ask Claude: "Can you parse this listing for me?" and paste the URL.

---

## Step 1: Install uv

`uv` is a lightweight tool that runs Python programs without requiring you to install Python yourself.

**Ask the user to open Terminal** (Spotlight → type "Terminal" → press Enter).

Run this command:
```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After it finishes, close Terminal and open a new Terminal window (this makes the new tool available).

Verify it worked:
```
uv --version
```

Expected: a version number like `uv 0.4.x`. If you see "command not found", the install didn't finish — try running the install command again.

---

## Step 2: Find the Claude Desktop config file

The config file tells Claude Desktop which tools to load. It lives at:
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Ask the user to open Finder**, then:
1. In the menu bar, click **Go** → **Go to Folder...**
2. Type: `~/Library/Application Support/Claude/`
3. Press Enter
4. Look for a file called `claude_desktop_config.json`

If the file does not exist yet, it needs to be created — that is fine, the next step handles it.

If the file exists, open it in TextEdit (right-click → Open With → TextEdit).

---

## Step 3: Add SEParser to the config

The config file is JSON. There are two cases:

**Case A — file is empty or does not exist:**
The full contents of the file should be:
```json
{
  "mcpServers": {
    "separser": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/siyuanligit/separser", "separser-mcp"]
    }
  }
}
```

**Case B — file already has content (other tools are configured):**
Find the `"mcpServers"` section and add the separser block inside it. Example — if the file currently looks like:
```json
{
  "mcpServers": {
    "some-other-tool": { ... }
  }
}
```

Add a comma after the existing tool's closing `}` and then add:
```json
    "separser": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/siyuanligit/separser", "separser-mcp"]
    }
```

Save the file (Cmd+S).

---

## Step 4: Restart Claude Desktop

Quit Claude Desktop completely (Cmd+Q, or right-click the dock icon → Quit — not just close the window).

Reopen Claude Desktop.

**The first time SEParser loads**, it will automatically download and install Chromium (a headless browser it uses to fetch listing pages). This takes about 1–2 minutes and happens silently in the background. No action needed.

---

## Step 5: Verify it works

In Claude Desktop, start a new conversation and say:
> "Can you parse this listing for me? https://streeteasy.com/building/schaefer-landing-south/7d"

Claude should respond with structured property data including price, beds, baths, building details, and more.

If Claude says it does not have a `parse_listing` tool or cannot find SEParser, the config file likely has a syntax error. Ask the user to share the contents of the config file so you can check it.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `uv: command not found` after install | Open a new Terminal window and try again |
| Claude says it can't find the tool | Config file not saved, or Claude Desktop not fully restarted |
| "Cloudflare block" error on parse | Temporary — wait 30 seconds and try again |
| "Login wall" error on parse | The listing requires a StreetEasy account to view |
| Chromium download taking long | First-run only — wait for it to finish, then try again |
