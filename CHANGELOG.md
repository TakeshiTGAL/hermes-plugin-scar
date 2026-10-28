# Changelog

## 0.2.4

- An unattended platform is the platform bound for this turn. A webhook, msgraph_webhook, or api_server turn does not forget a scar when that name is absent from the process environment, including after always and under yolo.
- Each scar_forget call uses a new rule key. Choosing always does not cover the next forget.
- The thirty-second config stamp is `_config_version` 50, the stamp in Hermes 0.22.2.

## 0.2.3

- The opening lines name advisor, the agent-station file-edit replay, hermes-memory-pane memory changes, and llmslim's local compression as separate facts.

## 0.2.2

- A session that has the skills tools adds one line, `scar:keep-a-scar`, to the system prompt skills index. That line stays when the scar tools are turned off. A session started with `-t terminal,scar` has no skills index line. The startup list of available skills does not include this skill.

## 0.2.1

- A ledger that cannot be parsed no longer stops a terminal command whose shape cannot be read. A value over 200,000 characters, a shell nested past 8 levels, or more than 8 wrapper words runs. An rm command whose danger tokens were read still stops.
- A forget question is sent only when the whole text fits on the Hermes 0.22.2 CLI card at 100 columns and 24 rows, which leaves 7 description lines of 63 columns. A longer question is not sent, and the scar stays, including when yolo or approvals off would skip the card.

## 0.2.0

- Compare only a tool that has a scar, and only under the argument keys that scar kept. Other tools and other keys are not read.
- Peel wrapper words in a loop: a known wrapper list plus up to two other leading words. A sentence or a long list of file names is no longer "not compared" and is no longer blocked.
- Raise the text limit for a kept key to 200,000 characters.
- A ledger that cannot be parsed stops only a terminal command with an rm danger token. Other calls run.
- Run Hermes's public redactor after the plugin's own patterns, and add patterns for secret assignments, hf_, glpat-, AIza, sshpass -p, and mysql -p. scar_list masks each preview again.
- Add scar_forget. It removes one scar after the person approves it on the Hermes card, with a rule key for that scar only. Cron, a single query, a webhook, msgraph_webhook, an api_server session, and a plugin host cannot forget a scar, including after always and including under yolo. Hermes 0.21.6 or newer is required so that check can read the public cron identity.
- A deny on a plugin, computer_use, or SSH config card is not kept as a scar.

## 0.1.0

- Keep a scar when a person denies an rm command on the Hermes approval card.
- Stop a later call with the same shape before the tool runs.
- Stamp the receipt with the local clock, including the weekday and the numeric offset.
- Read an rm inside a shell -c body and inside env, and tell the agent not to paraphrase a blocked command.
