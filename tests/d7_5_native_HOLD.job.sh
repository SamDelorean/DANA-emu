#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Local Git HOLD only. No Commander, build, queue action or automatic launch.
set -euo pipefail
if [[ ${DANA_D75_NATIVE_AUTHORIZED:-NO} != YES ]]; then
    echo 'HOLD: fresh explicit D7.5 native authorization required' >&2
    exit 3
fi
# Arguments: --diag ABSOLUTE_EXISTING_DIAG --diag-sha256 MEASURED_NEW_SHA
# --source EXISTING_CANONICAL_SKELETON_DIRECTORY --output NEW_EVIDENCE_DIRECTORY
# Only newly generated disposable media are ever used by this campaign.
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec timeout --signal=TERM --kill-after=10 1800 python3 "$script_dir/d7_5_native.py" "$@"
