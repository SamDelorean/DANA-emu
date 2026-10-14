# DANA-emu pre-publication review — 2026-10-13

**Audited scope:** repository `SamDelorean/DANA-emu`, baseline `43a88dfdbe0dd6ca02fda1b02d830c77785082fb`, default branch `main`. This review records technical findings; **it is not legal advice and does not authorize copying third-party works**.

## Inventory and findings

- At that revision, **10 text files** were reviewed in the main tree (README, eight files under `docs/` and `research/sources.lock.json`). No project-owned or third-party C/C++ source, firmware, ROM images, executables, private keys, identifiable tokens or dumped device data were found.
- File changes across **24 commits** were inspected and remained within that documentary set; no revision added binary or firmware files. At audit time, only `main` was observed, without pull requests or releases.
- Structured searching of common credential formats in contents and historical diffs returned no matches. **No automated search can guarantee the complete absence of confidential material.**
- `research/sources.lock.json` contains reference paths, GitHub links, commits and licensing notes; **it contains neither downloaded source files nor ROM material**.
- References to `Dana-OS3K` lead to **a separate private repository**. Making DANA-emu public **does not** publish Dana-OS3K. Visitors without access may see errors when following those links.
- `docs/WORKFLOW_AS2K.md` names local paths on machine T, including a home directory. No secrets were identified in those paths, but they remain visible in history if repository visibility is changed in place.
- GitHub may expose repository history, commit metadata, future Actions runs and logs; readers can clone and fork the repository.

## Intellectual property and distribution

1. **Current documentary design:** technical references, observable hardware facts, register names and links are not equivalent to incorporating protected source files from another implementation. This does not establish independent authorship of every phrase or override its authors' rights.
2. **MAME:** the project as a whole is distributed under GPL-2.0-or-later, while many files are BSD-3-Clause. Before incorporating or distributing particular components, review **each file's SPDX/license header**, notices and the obligations of any combined distribution. The MAME name and logo are not ours. Documentation: https://docs.mamedev.org/license.html
3. **EmuTOS-Dana and POSE/Retro68:** cited as GPL references. Do not directly copy or combine implementations without reviewing license compatibility, rights and obligations. **neo-re, whose license has not been verified, remains a technical reference rather than automatically reusable code.**
4. **Commercial AlphaSmart/Palm ROM/firmware:** do not publish original files, Flash images, dumps, bytes extracted from updaters, modified firmware derived from proprietary software, or user/device data. Executability in an emulator does not grant redistribution rights.
5. **Trademarks and affiliation:** AlphaSmart, Dana, Palm, MAME and other names are used for technical description only. This independent project does not claim endorsement by the respective holders.
6. **No LICENSE:** no `LICENSE` was present at audit time. Publishing documentation **does not automatically grant an open-source license**. Without an explicit license, reuse by others remains governed by applicable copyright rules. Select a future license for project-owned code separately, after determining what external sources will be incorporated. Source: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository

## Mandatory criteria before adding files

- Do not commit credentials, tokens, private configurations, secret-bearing paths or third-party information without consent.
- Do not store commercial ROM/Flash/firmware, snapshots or media containing real user data, or protected compiled binaries in Git.
- Every incorporated third-party file must have recorded provenance, copyright, license and distribution obligations and be legally compatible with its destination; a source link is not permission to copy.
- Apply the root's conservative `.gitignore` as a first safeguard, **without relying on it to remove already committed or historical content**.
- Audit Actions workflows **before** publication: avoid printing secrets in logs or uploading protected artifacts, and use minimal `GITHUB_TOKEN` permissions.

## GitHub Actions — cost reality

At the time of this review, standard **GitHub-hosted Actions runners** are free for public repositories. **Larger runners remain billable**, and artifact/cache storage remains subject to quotas and billing policies. Making a repository public does not provide unlimited free use of Copilot, Codex or every premium GitHub feature. Official documentation: https://docs.github.com/en/billing/concepts/product-billing/github-actions

The audited tree **does not yet contain `.github/workflows/` workflows**: making it public alone will not trigger compilation or automated checks. Suitable tests or workflows must first be added for each increment while preserving mandatory functional qualification on T.

## Visibility review

This note and `.gitignore` prepare publication, but **do not change visibility**. Afterwards, confirm on GitHub that `visibility = public`, and review exposed logs and history. Returning from public to private later **does not retract forks or copies already made**.

## Technical continuation at the time of this audit

The authoritative plan remains `docs/DANA_EMU_INCREMENTAL_WORK_PLAN.md`: D0.1 documentary `SPEC_READY`, next increment **D0.2 (MC68328/EZ/VZ equivalence)**. This historical review did not run Commander, compile the emulator or close any hardware test. For the current cursor consult [canonical continuity](CANONICAL_CONTINUITY_AND_RULES.md); historical cursor descriptions are not current.
