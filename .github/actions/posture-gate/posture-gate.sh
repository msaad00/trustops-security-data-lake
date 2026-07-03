#!/usr/bin/env bash
# TrustOps posture gate — evaluate /api/v1/posture/current against thresholds.
set -euo pipefail

TRUSTOPS_URL="${TRUSTOPS_URL:-}"
TRUSTOPS_API_TOKEN="${TRUSTOPS_API_TOKEN:-}"
MIN_SCORE="${MIN_SCORE:-0}"
MAX_CRITICAL_VIOLATIONS="${MAX_CRITICAL_VIOLATIONS:-0}"
MAX_OPEN_VIOLATIONS="${MAX_OPEN_VIOLATIONS:--1}"
FAIL_ON_STALE_EVIDENCE="${FAIL_ON_STALE_EVIDENCE:-false}"

if [[ -z "${TRUSTOPS_URL}" ]]; then
  echo "::error title=TrustOps posture gate::TRUSTOPS_URL is required"
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "::error title=TrustOps posture gate::jq is required on the runner"
  exit 1
fi

base="${TRUSTOPS_URL%/}"
endpoint="${base}/api/v1/posture/current"

curl_args=(-fsS -H "Accept: application/json")
if [[ -n "${TRUSTOPS_API_TOKEN}" ]]; then
  curl_args+=(-H "Authorization: Bearer ${TRUSTOPS_API_TOKEN}")
fi

response=""
if ! response="$(curl "${curl_args[@]}" "${endpoint}")"; then
  echo "::error title=TrustOps posture gate::Failed to reach ${endpoint}"
  exit 1
fi

if ! echo "${response}" | jq -e '.data.posture' >/dev/null 2>&1; then
  detail="$(echo "${response}" | jq -r '.errors[0].detail // "unexpected response"')"
  echo "::error title=TrustOps posture gate::${detail}"
  exit 1
fi

posture="$(echo "${response}" | jq -c '.data.posture')"
score="$(echo "${posture}" | jq -r '.score // empty')"
state="$(echo "${posture}" | jq -r '.state // "unknown"')"
open_count="$(echo "${posture}" | jq -r '.open_violation_count // 0')"
critical_count="$(echo "${posture}" | jq -r '.critical_violation_count // 0')"
stale_count="$(echo "${response}" | jq -r '.data.posture.stale_evidence_count // .data.evidence_freshness.stale_count // 0')"

if [[ -z "${score}" ]]; then
  echo "::error title=TrustOps posture gate::Posture score missing from TrustOps response"
  exit 1
fi

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  {
    echo "posture_score=${score}"
    echo "posture_state=${state}"
    echo "open_violation_count=${open_count}"
    echo "critical_violation_count=${critical_count}"
  } >>"${GITHUB_OUTPUT}"
fi

echo "TrustOps posture gate"
echo "  score: ${score}"
echo "  state: ${state}"
echo "  open violations: ${open_count}"
echo "  critical violations: ${critical_count}"
echo "  stale evidence rows: ${stale_count}"

failures=()

if awk -v score="${score}" -v min="${MIN_SCORE}" 'BEGIN { exit (score + 0 >= min + 0) ? 0 : 1 }'; then
  :
else
  failures+=("posture score ${score} is below minimum ${MIN_SCORE}")
fi

if awk -v count="${critical_count}" -v max="${MAX_CRITICAL_VIOLATIONS}" 'BEGIN { exit (count + 0 <= max + 0) ? 0 : 1 }'; then
  :
else
  failures+=("critical violations ${critical_count} exceed maximum ${MAX_CRITICAL_VIOLATIONS}")
fi

if [[ "${MAX_OPEN_VIOLATIONS}" != "-1" ]]; then
  if awk -v count="${open_count}" -v max="${MAX_OPEN_VIOLATIONS}" 'BEGIN { exit (count + 0 <= max + 0) ? 0 : 1 }'; then
    :
  else
    failures+=("open violations ${open_count} exceed maximum ${MAX_OPEN_VIOLATIONS}")
  fi
fi

if [[ "${FAIL_ON_STALE_EVIDENCE}" == "true" && "${stale_count}" != "0" ]]; then
  failures+=("stale or expired evidence on ${stale_count} control(s)")
fi

if ((${#failures[@]} > 0)); then
  for reason in "${failures[@]}"; do
    echo "::error title=TrustOps posture gate::${reason}"
  done
  exit 1
fi

echo "Posture gate passed."
