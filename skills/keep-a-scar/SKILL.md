---
name: keep-a-scar
description: Stop a command you denied once when that same shape comes back. Use scar_check or scar_list.
---

Hermes registers this skill as `scar:keep-a-scar`. It does not copy the file into the profile skills directory. A session that has the skills tools adds one line for this skill to the system prompt skills index. That line stays when the scar tools are turned off, because the plugin is still enabled. `skills_list` returns the name in that session. Load this file with `skill_view` and the name `scar:keep-a-scar`. A chat started with `-t terminal,scar` does not include `skills_list`, `skill_view`, or `skill_manage`. That screen says the skills toolset is disabled, and this file is not in the prompt. A model that has not loaded this file may still say to try again. That sentence does not run the command.

Before the person answers the approval card, write the command, the tool name, and what a deny will save. Do not invent a recorded time. The plugin clock writes the weekday and the numeric offset.

## When the card appears

Hermes has no button named never. `hermes chat --cli` shows a numbered menu. The highlight starts on 1. Allow once. The next rows are Allow for this session, Add to permanent allowlist, and 4. Deny. The person presses 4. That key selects Deny and confirms it. Enter confirms whichever row is highlighted, so Enter on the opening highlight allows the command once. Typing never does not move the highlight. Do not tell the person to type never.

Choosing once, session, or always does not keep a scar, and Hermes may then allow that dangerous pattern without asking again. The plugin stores only the choice id deny.

If the command is an rm shape with danger tokens, a deny keeps the tool name, the argument keys that carried those tokens, and the token set. A shell -c body is part of that shape. A path is not kept as identity. Quote the command you expect, for example rm -rf ./build, and say that a later call with the same tokens will be stopped before it runs.

## After a deny

A later call that includes every token on the scar is blocked. Quote the block line. It names the scar number, the weekday, the clock, the numeric offset, and the words you pressed deny. It also says not to paraphrase the command and not to run it again. Do not replace that clock with a time of your own. Once this skill is loaded, do not offer to try again. Do not rephrase the command into another tool call.

scar_check compares one call and does not run it. scar_list reads the ledger and does not change it. scar_forget removes one scar, and only after the person approves it on the Hermes card. Each forget asks again. Answering always does not cover the next forget. The question is sent only when it fits in 7 lines of 63 columns. A longer question is not sent, and the scar stays. It does not run in cron, a single query, a webhook, an api_server session, or a plugin host, even after always. Call it only when the person asks to forget that scar. Do not call it to get past a block. One stored scar is reported as 1 scar. If the ledger file is absent, say the file is absent. If the file cannot be read, say it could not be read. Do not say there are no scars unless the file was read and it held none.

A person on a gateway platform can ask for scar_list and will see the redacted preview. Say that when you list scars.

## What a deny does not keep

A command with no rm danger tokens, such as ls, is not stored and does not block later calls of that tool. Only a tool with a scar is compared, and only under the argument keys that scar kept. A sentence, a list of file names, and every other tool are not read. Echo of the words is not the command. python -c, node -e, a script file, and command substitution are not the shape. An unattended session and an isolated plugin process do not store a new scar, because no person answered. A scar that is already stored still blocks on every surface, including yolo and cron.

## What this plugin does not do

It does not run the blocked tool. It does not call a model. It does not send the ledger off this computer. It does not create a cron job. It does not add a second prompt when yolo or approvals off already skipped the Hermes card.

## When it fails

- bad_argument: Fix the named field. Nothing was written.
- ledger_unreadable: The file is present but could not be parsed. Leave it in place.
- ledger_full: The ledger is at its cap. Nothing was written.
- shape_invalid: The tool name or the arguments cannot be compared.
- not_found: No scar has that id. Call scar_list for the ids that exist. Nothing was written.
- unattended: Nobody is present to forget a scar. Nothing was written.
- internal: Retry once. If it repeats, say the tool failed.
