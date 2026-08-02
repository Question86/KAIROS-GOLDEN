# KAIROS Golden Starter

KAIROS is a small, governed infrastructure for starting either a manual or an autonomous
project without carrying project history into the next one. The repository contains a
sealed source-only starter, a Loop 1 archive, and no developer task history.

## Start a project

From the cloned repository:

```powershell
cd kairos_harness
python -m kairos starter-check --workspace ../kairos_workspace
python -m kairos goal-prompt --workspace ../kairos_workspace --idea "Describe the project idea here"
```

The second command prints one English `/goal` prompt. Copy it unchanged into Codex or
Claude Code. The LLM first formulates an explicit kickoff contract, then runs the
governed `project-kickoff` command. That one command verifies and materializes the
starter, creates the first goal and task, and atomically opens Loop 2.

After kickoff, KAIROS requires task-first work, metadata-first research, documented
evidence, and verified finalization. The bootstrap prompt supports either a Human-led or
autonomous workflow; it does not bypass those safeguards.

The golden seal is immutable. Ongoing project work belongs in a repository created from
this template, never in the template repository itself.

## License

Copyright (c) 2026 Yannick Wende. KAIROS is distributed under the KAIROS Personal and
Private Use License v1.0. It permits personal, private, non-commercial use and local
modification; it does not permit redistribution, public hosting, sublicensing, or
commercial use. Read [LICENSE](LICENSE) before use.
