# DANA-emu publication aside and Git language policy

**Recorded:** 2026-10-13  
**Scope:** `SamDelorean/DANA-emu` only.  
**Purpose:** Retain work discussed during an unrelated AS2K Stock Energy conversation without affecting AS2K's authoritative plan, cursor, evidence, or execution permissions.

## Completed publication-readiness work

The user requested a legal/provenance screening and considered making this repository public to use standard GitHub Actions runners without per-minute compute charges. The work was already documented and merged in [publication-readiness PR #1](https://github.com/SamDelorean/DANA-emu/pull/1). The resulting artifacts are [publication review](PUBLICATION_REVIEW_20261013.md), the root `.gitignore`, and the README provenance disclaimer.

The audit at that time inspected ten textual tracked files and 24 historical commits, with no commercial firmware, ROM files, executables, or typical secret patterns detected. This is a **limited technical screening, not a legal opinion or an absolute confidentiality guarantee**. Its scope is captured in the publication review; newer content must be checked independently.

**Visibility was not changed.** A fresh repository check during this record showed `private`. Changing it to `public` requires the owner's separate, deliberate administrative action and exposes historical commits and any forks thereafter. Merely adding this note does **not** authorize or perform the visibility change.

**Costs:** Standard GitHub-hosted Actions runners are generally free for public repositories under GitHub's current public-repository rules. This does not make larger runners, artifact/storage usage beyond applicable policies, Codex, or Copilot automatically free. Publishing alone does not create Actions workflows.

**Legal separation:** Do not commit redistributable commercial Dana/AlphaSmart/Palm ROM/Flash images or unlicensed third-party code. Evaluate the exact SPDX/header licenses of any copied MAME, EmuTOS, POSE, Retro68 or other components before redistribution. Public visibility is not an open-source license; do not infer a grant of reuse rights when a `LICENSE` file is absent.

## Git language preference — effective for future work

The user's standing instruction is that **all Git work must be in English**. In this repository, use English for new/modified documentation, README additions, code and comments, filenames and symbols, commit messages, branch names, pull requests, issues, tests, scripts, manifests, checkpoints, and CI logs under the project's control.

Existing Spanish historical documents and commit history may remain unchanged to preserve provenance. Convert or supplement existing documents in English only when they are substantively edited; do not force an unrelated bulk translation. Conversation with the user may remain in Spanish. This is a language/presentation rule, **not permission to revise the agreed technical architecture**.

## Canonical technical continuation

This aside is entirely separate from the Dana emulator development increment. **Do not reset, advance, or reopen its work plan because of publication or language changes.** The latest [handoff](HANDOFF.md) identified **D0.3** as the next task after D0.1 and D0.2 were marked `SPEC_READY`, with EmuTOS-Dana guest image and loader contract as the focus. Read [the authoritative incremental plan](DANA_EMU_INCREMENTAL_WORK_PLAN.md) and current Git state before work.

Likewise, this Dana record must not be added as an item, dependency, gate, or authorization in the separate **AS2K Stock Energy** project. Its R13A PowerIdle work must resume exclusively from its own canonical Git cursor and evidence.

**No emulator, Commander, or Actions workflow was launched as part of this record.**
