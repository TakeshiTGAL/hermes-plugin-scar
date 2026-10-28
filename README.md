# scar

scar keeps the tool-call shape you denied on a Hermes approval card and stops that shape before it runs. It never calls a model. The second-model review on every turn is advisor. agent-station shows file-edit replay on its read-only Desktop page. hermes-memory-pane changes memory entries from its Desktop pane. Older tool output is compressed on this computer by llmslim, and llmslim makes no model call.

Hermes has no button named never. `hermes chat --cli` shows a numbered menu. The highlight starts on `1. Allow once`, then `2. Allow for this session`, `3. Add to permanent allowlist`, and `4. Deny`. Press 4. That key selects Deny and confirms it. The card footer says to use the arrow keys and Enter. Enter confirms the highlighted row. Do not press Enter while the highlight is still on Allow once: the command runs. The digit 4 selects Deny and confirms it without Enter. Typing never does not move the highlight. The plugin stores the choice id deny and no other choice. The block line says you pressed deny, and it tells the agent not to paraphrase the command and not to run it again. Choosing once, session, or always does not keep a scar, and Hermes may then allow that dangerous pattern without asking again.

## What is stopped

A scar stores the tool name, the argument keys that contained an rm command, and the danger tokens. The path is not part of the match. These commands are the same scar: `rm -rf`, `rm -fr`, `rm -r -f`, `rm --recursive --force`, a flag after the path, `/bin/rm`, a wrapper in front, `find` with `-exec rm -rf`, and the same rm inside a shell `-c` body. A wrapper is one of `nice`, `nohup`, `time`, `timeout`, `xargs`, `command`, `exec`, `builtin`, `stdbuf`, `ionice`, `setsid`, `caffeinate`, `chronic`, and `doas`, with its flags, or up to two other leading words with their flags, such as `git rm -rf`. The shells are `sh`, `bash`, `dash`, `zsh`, `ksh`, and `ash`, including a short flag cluster that contains `c` such as `-lc`, and including a wrapper in front of the shell. `env` is read with its flags and assignments, then `rm` or a shell `-c`. That covers `env -u PATH rm -rf`, `env -i rm -rf`, `env FOO=1 rm -rf`, and `env bash -c 'rm -rf ...'`. `busybox sh -c` is read. Nested shells are read up to 8 deep, and up to 8 wrapper words in front of one command. Extra argument keys such as timeout do not split the scar. A later call is stopped when it includes every token the scar kept. `rm -r` does not match a scar that also kept force.

Only a tool that has a scar is compared, and only under the argument keys that scar kept. Every scar from the card is a `terminal` scar under `command`, so `read_file`, `write_file`, `web_search`, `send_message`, and every other tool are not read at all. In the terminal, `ls`, `touch` with nine file names, `git add` with eight files, and `echo rm -rf is dangerous` are not that shape. After two leading words that are not rm, the rest of a command is not read as rm, so a sentence of any length is not the shape. A data command such as `echo` or `printf` does not contribute the words it prints, so `echo 'bash -c "rm -rf ..."'` is not the scar. These spellings are not read either: `python -c`, `perl -e`, `node -e`, `ruby -e`, a script file such as `bash ./script.sh`, command substitution and backticks, and a `--` before `-c`. A command with no danger tokens is not stored, and it does not block the whole tool. On a tool that has a scar, a value under a kept key that is longer than 200,000 characters, a shell nested past 8 levels, or more than 8 wrapper words in front of one command is not compared, and that call is not run. If the ledger file cannot be parsed, a `terminal` command that carries an rm danger token is not run, and every other call runs. A value longer than 200,000 characters, a shell nested past 8 levels, or more than 8 wrapper words is not read as that command, and that call runs. The file is left in place. A person can move `plugin-data/scar/ledger.json` aside in the Hermes home to start a new ledger. Reading with `scar_check` or `scar_list` does not create the file and does not replace a broken one.

The ledger is read on every foreign tool call. The file is at most 800KB and holds at most 200 scars. A block applies on every surface, including yolo, cron, the gateway, and approvals off, once a scar exists. Cron, a single-query session, a webhook, `msgraph_webhook`, `api_server`, and an isolated plugin process do not store a new scar, because no person answered. A scar that is already stored still blocks there. Yolo and approvals off skip the Hermes prompt, and this plugin does not add a second prompt.

A person who can talk to the agent through the gateway can ask it to call `scar_check`, `scar_list`, and `scar_forget`. `scar_list` returns each scar, including the redacted preview of the denied command. The tools are the toolset `scar`. Remove them from one platform with `hermes tools disable scar --platform <platform>`. Platform names include `cli`, `telegram`, `discord`, `slack`, and `cron`. There is no platform named gateway. `hermes tools list --platform <platform>` shows the names this Hermes accepts. That command hides the tools on that platform. It does not stop the block. `post_approval_response` records a deny. `pre_tool_call` still blocks on every surface while the plugin is enabled. To stop the block, disable the plugin. A running gateway keeps the hook until it restarts.

The receipt clock is the plugin clock in your zone, with the weekday and a numeric offset such as +09:00. The agent cannot set that time. In `hermes chat --cli`, Hermes hands the hook the command before its own masking, so the plugin removes secret-shaped text itself before the preview is written: its own patterns (assignments such as `AWS_SECRET_ACCESS_KEY=`, `hf_`, `glpat-`, `AIza`, `ghp_`, `xoxb-`, `sk-`, `AKIA`, `sshpass -p`, `mysql -p`, URL passwords, and long hex) and then Hermes's public redactor with `force=True`, which keeps only the prefix of a key it knows. `scar_list` masks each preview again when it reads the file. A secret shape that neither knows can stay in the preview. Nothing leaves this computer. This plugin does not call a model and does not create a cron job. There is no daily limit. The tools stay available until `hermes tools disable scar`.

## Forget a scar

A scar stays on every surface until it is forgotten or the plugin is disabled. `scar_forget` takes a scar id from `scar_list`. Before it runs, the plugin's `pre_tool_call` hook returns the Hermes approve directive when the whole question fits on the card. The question names the scar number, the weekday, the clock, the token set, the redacted preview, and the sentence that the shape is no longer stopped. The Hermes 0.22.2 CLI card at 100 columns and 24 rows shows 7 description lines of 63 columns. A longer question is not sent, and the scar stays. Deny, or no answer, leaves the scar in place, and the hook does not keep that deny as a new scar. Hermes does not call the tool after it blocks the call. Each forget asks again. The rule key changes on every call, so choosing always does not cover the next forget. Hermes may add one allowlist line to `config.yaml`, and that line does not match the next call. Forgetting needs a person because a scar is a person's deny: the agent must not lift its own block. Yolo and approvals off skip that card in a session a person started when the question fits, so there the agent can forget that scar without a second prompt. Cron, a single query, a webhook, `msgraph_webhook`, `api_server`, and a plugin host do not forget a scar. The hook blocks `scar_forget` before Hermes's gate, including after always and including when yolo is on. It reads the platform bound for this turn, so a webhook, `msgraph_webhook`, or `api_server` turn is blocked when that name is absent from the process environment. Hermes checks a permanent allowlist before its own cron deny, so this plugin does not rely on that deny. The file can also be edited by hand while Hermes is stopped. A file that no longer parses stops only an rm command whose shape was read, until it is moved aside. A command whose shape cannot be read still runs. While the plugin is enabled, it registers a read-only skill as `scar:keep-a-scar`. Hermes does not copy that file into the profile skills directory, and it does not add the skill to the startup list of available skills. A session that has the skills tools adds one line for that skill to the system prompt skills index. That line stays when the scar tools are turned off, because the plugin is still enabled. `skills_list` returns the name in that session. The thirty-second chat uses `-t terminal,scar`, which leaves `skills_list`, `skill_view`, and `skill_manage` out. That screen says the skills toolset is disabled, and the prompt has no skills index line for this skill.

## Tools

`scar_check` compares one call and does not run it. `scar_list` reads the ledger and does not change it. If the file is absent, the result says the file is absent. It does not say there are zero scars. `scar_forget` removes one scar after the person approves it on the Hermes card. It is the only tool that writes the file.

## Install

Install this directory with Hermes 0.21.6 or newer. An unattended forget reads the public cron identity, which that release added, and also the cron mark, the single-query mark, the platform bound for the turn, and the plugin-host mark. The install scan verdict is safe, with 15 medium findings, all in the test tree. The install does not need `--force`. Set `HERMES_HOME` to a profile you intend to use. Do not point it at a profile you did not choose.

## Pinned local model

The plugin does not download files and does not start a server. Before the scene, check the files yourself. If a hash differs, do not use that file.

| File | Identity | sha256 |
| --- | --- | --- |
| llama.cpp archive `llama-b11669-bin-macos-arm64.tar.gz` | 0.7.0-dev build 11669, commit 620d2225cc436ab0b001e3200e590e3b286ef9ab | dbed55493d72bc1ba2babc8770d669c2289b5bc4ee9fb2a4dfc158d45b7d13fd |
| `Qwen3-0.6B-Q8_0.gguf` | 639446688 bytes | 9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031 |

`llama-server --version` prints `0.7.0-dev (build 11669, commit 620d2225c)`.

## Thirty seconds

Use an empty `HERMES_HOME`. The server listens on loopback only. The child environment for the server is `PATH`, `HOME`, `TMPDIR`, and `LANG`. Do not pass the rest of the process environment.

```sh
export HERMES_HOME="$(mktemp -d)"
export HERMES_INTERACTIVE=1
shasum -a 256 /path/to/Qwen3-0.6B-Q8_0.gguf
shasum -a 256 /path/to/llama-b11669-bin-macos-arm64.tar.gz
env -i PATH="$PATH" HOME="$HOME" TMPDIR="${TMPDIR:-/tmp}" LANG="${LANG:-C.UTF-8}" \
  /path/to/llama-server \
  -m /path/to/Qwen3-0.6B-Q8_0.gguf \
  --host 127.0.0.1 --port 9931 --jinja \
  --device none --fit off -ngl 0 --reasoning off -c 64000
```

This build caps the slot at the model's training context, 40960, even when `-c` is higher. Hermes still refuses a local endpoint whose configured window is below 64000, so the home config sets `context_length` to 64000. Startup then logs one warning: the pin wins over the provider's advertised window, and the warning says to remove `model.context_length` from `config.yaml` to use that advertised window. For the id `GET /v1/models` returns for this file, the advertised window is the qwen family catalog value, 131,072, not the server slot. This scene keeps the pin. The card is reached with the pin left in place. Removing the pin is not part of this scene. Start the chat with `-t terminal,scar`. That is the terminal tool plus the scar tools. The full default tool list is large enough that this 0.6B model calls `write_file` and never opens the card. The scene reply is not cut by the 40960 slot. Set `model.default` to the id `GET /v1/models` returns. Point `base_url` at `http://localhost:9931/v1`. The two values must match, or Hermes drops the context override and stops.

Install this directory into that empty home with `hermes plugins install file://<this-directory>`. The scan does not need `--force`. Write the config after install. Do not run `hermes setup` on this home.

Write this `config.yaml` in the empty home. `_config_version` 50 is the stamp in the Hermes tree this scene starts, in `hermes_cli/config_defaults.py`. A file with no stamp is read as version 0. That is below the support floor of 12, so Hermes logs that the config predates version 12 and names `hermes setup`. `hermes setup` rewrites `config.yaml` and can drop the model pin and the plugin list. With this stamp, startup leaves the file in place. If the Hermes you start publishes a different integer, write that integer instead.

```yaml
_config_version: 50
model:
  default: <id from GET /v1/models>
  provider: custom
  base_url: http://localhost:9931/v1
  context_length: 64000
plugins:
  enabled:
    - scar
approvals:
  mode: manual
agent:
  coding_context: off
  stall_guards: false
  task_completion_guidance: false
  parallel_tool_call_guidance: false
  environment_probe: false
  bot_mode_protocol: false
  tool_use_enforcement: false
  execution_guidance: false
platform_hints:
  cli:
    replace: "Write plain text."
tools:
  tool_search:
    enabled: off
telemetry:
  shared_metrics:
    enabled: false
    send: false
    offer_version: 2
auxiliary:
  title_generation:
    enabled: false
  free_only: true
compression:
  enabled: false
```

Write this `SOUL.md` in the same home. A 0.6B model copies the mid-turn steering example instead of calling a tool when this file is longer.

```markdown
You are a local assistant. Use the tool-call channel, not prose, when a tool can do the job.
```

Start `hermes chat --cli -t terminal,scar` with `HERMES_HOME` set to that home. `--cli` is the classic numbered menu. It is not the plain line `Choice [o/s/a/D]`. `-t terminal,scar` is the terminal tool plus the scar tools. The welcome screen says the skills toolset is disabled. Say: use the terminal tool to remove the directory named `foo-does-not-exist`. When the Dangerous Command panel shows `rm -rf` or the same flags under another spelling, the highlight is on `1. Allow once`. The panel footer says to use the arrow keys and Enter. Press 4. That selects Deny and confirms it. Do not press Enter first, and do not type never. The screen says the command was denied and did not run. The plugin writes one scar with its own clock.

Quit that chat and start `hermes chat --cli -t terminal,scar` again in the same home. Ask the same thing. Hermes tells the model not to retry inside the chat that just denied the command, so the same session often never makes the next call. A new chat does. A call that drops a danger token, such as a bare `rm`, is not this scar and is not blocked. Start another chat and ask again until the command still carries every token. That matching call is blocked before it runs, and no second card opens. The tool result contains `BLOCKED`, a weekday, a numeric offset, the words you pressed deny, and the words not to paraphrase the command and not to run it again. The model's own reply can still say to try again. That sentence does not run the command. The stop is the tool result. This skill is not in the prompt of `-t terminal,scar`, so this scene does not show the 0.6B model following the skill.

`scar_list` shows that one scar and does not change the file. The count line says `1 scar`. `ls`, `touch` with nine file names, and `read_file` are not blocked, and `write_file` with a sentence of notes is not read.

## Ledger

The file is `plugin-data/scar/ledger.json` under the active Hermes home. The JSON schema is `schemas/scar-ledger.schema.json`. Version 2 has no approval pairs. A receipt in the file is not trusted. The tools recompute the receipt from the scar id and the stored time.
