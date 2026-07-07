# Governance helpers are pure functions; these tests exercise payload contracts only.
from scripts.harness_loop_governance import (
    canonical_identity_key,
    classify_candidate,
    record_needs_transition,
    validate_governance_preflight_evidence,
    validate_depth_acquisition_smoke,
    validate_egress_proof,
    validate_source_profile_snapshot,
)


def _high_value_candidate(**overrides: object) -> dict[str, object]:
    candidate: dict[str, object] = {
        "candidate_id": "project:kserve",
        "url": "https://github.com/kserve/kserve",
        "decision_inputs": {
            "source_type_count": 2,
            "local_gap_level": "major",
            "duplicate_status": "none",
            "acquisition_path": "github_backfill",
        },
        "hard_gates": {
            "has_gap_proof": True,
            "has_two_source_types_for_deep_dive": True,
            "has_evaluator_scenario": True,
            "has_domain_channel_plan": True,
            "has_depth_acquisition_proof": True,
            "identity_key_is_canonical": True,
        },
        "priority_score": 10,
    }
    candidate.update(overrides)
    return candidate


def test_canonical_identity_key_normalizes_urls_and_tracking_noise() -> None:
    assert (
        canonical_identity_key(
            {
                "url": (
                    "HTTPS://Docs.VLLM.AI:443/en/latest/foo/"
                    "?utm_source=newsletter&gclid=x&page=2&version=v1#install"
                )
            }
        )
        == "url:https://docs.vllm.ai/en/latest/foo?page=2&version=v1"
    )

    assert (
        canonical_identity_key({"url": "http://Example.com:80/docs/?fbclid=abc&q=kernel"})
        == "url:http://example.com/docs?q=kernel"
    )


def test_canonical_identity_key_distinguishes_github_issue_pr_repo_and_release() -> None:
    assert (
        canonical_identity_key({"url": "https://github.com/KServe/KServe/issues/1222"})
        == "github-issue:kserve/kserve#1222"
    )
    assert (
        canonical_identity_key({"url": "https://github.com/KServe/KServe/pull/1222"})
        == "github-pr:kserve/kserve#1222"
    )
    assert (
        canonical_identity_key({"url": "https://github.com/vLLM-project/vLLM"})
        == "github-repo:vllm-project/vllm"
    )
    assert (
        canonical_identity_key({"url": "https://github.com/NVIDIA/TensorRT-LLM/releases/tag/v0.10.0-RC1"})
        == "github-release:nvidia/tensorrt-llm@v0.10.0-RC1"
    )


def test_canonical_identity_key_uses_publication_hardware_channel_source_and_raw_keys() -> None:
    assert (
        canonical_identity_key({"doi": "https://doi.org/10.1145/3676641.3716267"})
        == "doi:10.1145/3676641.3716267"
    )
    assert canonical_identity_key({"arxiv_id": "2401.01234v2"}) == "arxiv:2401.01234v2"

    sxm = canonical_identity_key(
        {"source_type": "hardware", "vendor": "NVIDIA", "model": "H200", "variant": "SXM 141GB"}
    )
    pcie = canonical_identity_key(
        {"source_type": "hardware", "vendor": "NVIDIA", "model": "H200", "variant": "PCIe 141GB"}
    )
    assert sxm == "hardware:nvidia:h200:sxm-141gb"
    assert pcie == "hardware:nvidia:h200:pcie-141gb"
    assert sxm != pcie

    assert (
        canonical_identity_key(
            {
                "source_type": "channel",
                "target_domain": "ai_infra",
                "base_url": "https://Docs.VLLM.AI:443/en/latest/?utm_campaign=x",
            }
        )
        == "channel:ai_infra:https://docs.vllm.ai/en/latest"
    )
    assert (
        canonical_identity_key({"source_type": "source_profile", "source_id": "src-vllm-docs"})
        == "source-profile:src-vllm-docs"
    )
    assert canonical_identity_key({"raw_sha256": "ABCDEF"}) == "raw-sha256:abcdef"
    assert (
        canonical_identity_key({"url": "https://example.com/report.pdf", "raw_sha256": "ABCDEF"})
        == "url:https://example.com/report.pdf"
    )


def test_classify_candidate_allows_high_value_only_when_hard_gates_and_inputs_pass() -> None:
    result = classify_candidate(_high_value_candidate())

    assert result["classification"] == "high_value"
    assert result["hard_gate_passed"] is True
    assert result["priority_score"] == 10
    assert result["identity_key"] == "github-repo:kserve/kserve"


def test_classify_candidate_keeps_priority_score_advisory_when_hard_gates_fail() -> None:
    candidate = _high_value_candidate(
        hard_gates={
            "has_gap_proof": True,
            "has_two_source_types_for_deep_dive": True,
            "has_evaluator_scenario": True,
            "has_domain_channel_plan": True,
            "has_depth_acquisition_proof": False,
            "identity_key_is_canonical": True,
        },
        priority_score=99,
    )

    result = classify_candidate(candidate)

    assert result["classification"] == "needs_more_evidence"
    assert result["priority_score"] == 99
    assert "has_depth_acquisition_proof" in result["missing_hard_gates"]


def test_classify_candidate_rejects_duplicate_and_missing_acquisition_path_for_high_value() -> None:
    duplicate = classify_candidate(
        _high_value_candidate(decision_inputs={**_high_value_candidate()["decision_inputs"], "duplicate_status": "duplicate"})
    )
    no_acquisition_path = classify_candidate(
        _high_value_candidate(decision_inputs={**_high_value_candidate()["decision_inputs"], "acquisition_path": "none"})
    )

    assert duplicate["classification"] == "low_value"
    assert no_acquisition_path["classification"] == "needs_more_evidence"


def test_record_needs_transition_moves_repeated_network_failure_into_needs_queue() -> None:
    item = {
        "identity_key": "url:https://kserve.github.io/website",
        "source_boundary": "host:kserve.github.io",
        "status": "blocked",
        "failure_history": [
            {
                "identity_key": "url:https://kserve.github.io/website",
                "source_boundary": "host:kserve.github.io",
                "failure_type": "dns",
                "status": "blocked",
                "finished_at": "2026-07-01T00:00:00Z",
            }
        ],
    }
    probe = {
        "identity_key": "url:https://kserve.github.io/website",
        "source_boundary": "host:kserve.github.io",
        "failure_type": "dns",
        "status": "blocked",
        "probe_url": "https://kserve.github.io/website",
        "started_at": "2026-07-08T00:00:00Z",
        "finished_at": "2026-07-08T00:00:01Z",
        "dns_status": "failed",
        "tls_status": "not_started",
        "http_status": None,
        "final_url": "",
        "error_class": "dns",
        "summary": "DNS lookup failed",
    }

    result = record_needs_transition(item, probe)

    assert result["status"] == "needs_network"
    assert result["needs_queue"] == "needs_network"
    assert result["wait_condition"] == "network_state_changed"
    assert result["next_probe_at"] == "2026-07-15T00:00:01Z"
    assert result["reprobe_due"] is False


def test_record_needs_transition_respects_ttl_and_returns_to_actionable_on_network_change() -> None:
    needs_item = {
        "identity_key": "url:https://kserve.github.io/website",
        "status": "needs_network",
        "needs_queue": "needs_network",
        "failure_type": "dns",
        "next_probe_at": "2026-07-15T00:00:01Z",
    }
    early_probe = {
        "identity_key": "url:https://kserve.github.io/website",
        "status": "blocked",
        "failure_type": "dns",
        "started_at": "2026-07-10T00:00:00Z",
        "finished_at": "2026-07-10T00:00:01Z",
    }

    early = record_needs_transition(needs_item, early_probe)

    assert early["status"] == "needs_network"
    assert early["reprobe_due"] is False

    recovered_probe = {
        "identity_key": "url:https://kserve.github.io/website",
        "status": "pass",
        "failure_type": "dns",
        "network_state_changed": True,
        "probe_url": "https://kserve.github.io/website",
        "started_at": "2026-07-16T00:00:00Z",
        "finished_at": "2026-07-16T00:00:01Z",
        "dns_status": "ok",
        "tls_status": "ok",
        "http_status": 200,
        "final_url": "https://kserve.github.io/website",
        "error_class": "",
        "summary": "HTTP reachable",
    }

    recovered = record_needs_transition(needs_item, recovered_probe)

    assert recovered["status"] == "actionable"
    assert recovered["needs_queue"] == ""
    assert recovered["reprobe_due"] is True
    assert recovered["network_state_changed"] is True


def test_record_needs_transition_requires_same_identity_or_host_for_network_recovery() -> None:
    needs_item = {
        "identity_key": "url:https://kserve.github.io/website",
        "status": "needs_network",
        "needs_queue": "needs_network",
        "failure_type": "dns",
        "next_probe_at": "2026-07-15T00:00:01Z",
        "last_probe": {
            "probe_url": "https://kserve.github.io/website",
            "source_boundary": "host:kserve.github.io",
            "failure_type": "dns",
        },
    }
    unrelated_recovered_probe = {
        "identity_key": "url:https://api.github.com/repos/kserve/kserve",
        "status": "pass",
        "failure_type": "dns",
        "network_state_changed": True,
        "probe_url": "https://api.github.com/repos/kserve/kserve",
        "started_at": "2026-07-16T00:00:00Z",
        "finished_at": "2026-07-16T00:00:01Z",
        "dns_status": "ok",
        "tls_status": "ok",
        "http_status": 200,
        "final_url": "https://api.github.com/repos/kserve/kserve",
        "error_class": "",
        "summary": "Unrelated host reachable",
    }

    result = record_needs_transition(needs_item, unrelated_recovered_probe)

    assert result["status"] == "needs_network"
    assert any("same identity_key or canonical host" in finding for finding in result["findings"])


def test_validate_egress_proof_requires_successful_external_http_probe() -> None:
    valid = {
        "probes": [
            {
                "probe_url": "https://api.github.com",
                "started_at": "2026-07-08T00:00:00Z",
                "finished_at": "2026-07-08T00:00:01Z",
                "dns_status": "ok",
                "tls_status": "ok",
                "http_status": 200,
                "final_url": "https://api.github.com/",
                "error_class": "",
                "summary": "GitHub API reachable",
            }
        ]
    }
    invalid = {
        "probes": [
            {
                "probe_url": "http://127.0.0.1:8765/api/health",
                "dns_status": "ok",
                "tls_status": "not_applicable",
                "http_status": 200,
            },
            {
                "probe_url": "https://api.github.com",
                "started_at": "2026-07-08T00:00:00Z",
                "dns_status": "failed",
                "tls_status": "not_started",
                "http_status": None,
            },
        ]
    }

    assert validate_egress_proof(valid) == []
    findings = validate_egress_proof(invalid)
    assert any("no successful external HTTP egress probe" in finding for finding in findings)
    assert any("probes[1].finished_at" in finding for finding in findings)


def test_validate_depth_acquisition_smoke_requires_bounded_multipage_or_multisource_evidence() -> None:
    valid = {
        "status": "pass",
        "identity_key": "github-repo:kserve/kserve",
        "acquisition_path": "github_backfill",
        "bounded": True,
        "max_items": 25,
        "source_types": ["closed_issues", "release_notes"],
        "items": [
            {"source_type": "closed_issues", "url": "https://api.github.com/repos/kserve/kserve/issues/1"},
            {"source_type": "release_notes", "url": "https://github.com/kserve/kserve/releases/tag/v0.15.0"},
        ],
    }
    invalid = {
        "status": "pass",
        "identity_key": "url:https://example.com/raw/links",
        "acquisition_path": "raw_links",
        "bounded": True,
        "max_items": 1,
        "source_types": ["raw_links"],
        "items": [{"source_type": "raw_links", "url": "https://example.com/raw/links"}],
    }

    assert validate_depth_acquisition_smoke(valid) == []
    findings = validate_depth_acquisition_smoke(invalid)
    assert any("at least two source types or multiple pages" in finding for finding in findings)
    assert any("single-page raw/links" in finding for finding in findings)


def test_validate_source_profile_snapshot_rejects_drift_and_sensitive_fields() -> None:
    snapshot = {
        "schema_version": 1,
        "captured_at": "2026-07-08T00:00:00Z",
        "record_counts": {"channels": 1, "sources": 1},
        "channels": [
            {
                "channel_id": "ch-ai-infra",
                "target_domain": "ai_infra",
                "base_url": "https://docs.vllm.ai/en/latest",
                "trust_level": "trusted",
                "auth_state": "none",
                "canonical_url": "https://docs.vllm.ai/en/latest",
                "identity_key": "channel:ai_infra:https://docs.vllm.ai/en/latest",
                "updated_at_watermark": "2026-07-08T00:00:00Z",
            }
        ],
        "sources": [
            {
                "source_id": "src-vllm-docs",
                "channel_id": "ch-ai-infra",
                "base_url": "https://docs.vllm.ai/en/latest",
                "fetcher_type": "sitemap",
                "schedule": "weekly",
                "probe_summary": {"status": "pass", "http_status": 200},
                "canonical_url": "https://docs.vllm.ai/en/latest",
                "identity_key": "source-profile:src-vllm-docs",
                "updated_at_watermark": "2026-07-08T00:00:00Z",
            }
        ],
    }
    db_rows = {
        "channels": {
            "ch-ai-infra": {
                "target_domain": "ai_infra",
                "base_url": "https://docs.vllm.ai/en/latest",
                "trust_level": "trusted",
                "auth_state": "none",
                "canonical_url": "https://docs.vllm.ai/en/latest",
                "identity_key": "channel:ai_infra:https://docs.vllm.ai/en/latest",
                "updated_at": "2026-07-08T00:00:00Z",
            }
        },
        "sources": {
            "src-vllm-docs": {
                "channel_id": "ch-ai-infra",
                "base_url": "https://docs.vllm.ai/en/latest",
                "fetcher_type": "sitemap",
                "schedule": "weekly",
                "canonical_url": "https://docs.vllm.ai/en/latest",
                "identity_key": "source-profile:src-vllm-docs",
                "updated_at": "2026-07-08T00:00:00Z",
            }
        },
    }

    assert validate_source_profile_snapshot(snapshot, db_rows) == []

    drifted = {
        **snapshot,
        "sources": [
            {
                **snapshot["sources"][0],
                "headers": {"Authorization": "synthetic-redacted-placeholder"},
                "updated_at_watermark": "2026-07-07T00:00:00Z",
            }
        ],
    }
    findings = validate_source_profile_snapshot(drifted, db_rows)
    assert any("sensitive key sources[0].headers" in finding for finding in findings)
    assert any("src-vllm-docs updated_at 2026-07-08T00:00:00Z is newer" in finding for finding in findings)

    invalid_time = {
        **snapshot,
        "channels": [{**snapshot["channels"][0], "updated_at_watermark": "not-a-time"}],
    }
    findings = validate_source_profile_snapshot(invalid_time, db_rows)
    assert any("channels[0].updated_at_watermark must be a valid timestamp" in finding for finding in findings)

    stale_counts = {
        "channels": {
            **db_rows["channels"],
            "ch-extra": {
                "target_domain": "ai_infra",
                "base_url": "https://extra.example",
                "trust_level": "trusted",
                "auth_state": "none",
                "canonical_url": "https://extra.example",
                "identity_key": "channel:ai_infra:https://extra.example",
                "updated_at": "2026-07-08T00:00:00Z",
            },
        },
        "sources": db_rows["sources"],
    }
    findings = validate_source_profile_snapshot(snapshot, stale_counts)
    assert any("record_counts.channels 1 does not match current DB count 2" in finding for finding in findings)

    sensitive_aliases = {
        **snapshot,
        "captured_at": "not-a-time",
        "sources": [
            {
                **snapshot["sources"][0],
                "auth_headers": {"x-api-key": "synthetic"},
                "session_cookie": "synthetic",
                "accessToken": "synthetic",
                "cookie_header": "synthetic",
            }
        ],
    }
    findings = validate_source_profile_snapshot(sensitive_aliases, db_rows)
    assert any("source profile snapshot captured_at must be a valid timestamp" in finding for finding in findings)
    assert any("sensitive key sources[0].auth_headers" in finding for finding in findings)
    assert any("sensitive key sources[0].session_cookie" in finding for finding in findings)
    assert any("sensitive key sources[0].accessToken" in finding for finding in findings)
    assert any("sensitive key sources[0].cookie_header" in finding for finding in findings)


def test_canonical_identity_key_rejects_incomplete_hardware_and_channel_candidates() -> None:
    assert canonical_identity_key({"source_type": "hardware", "vendor": "NVIDIA", "model": "H200"}) == ""
    assert canonical_identity_key({"source_type": "channel", "target_domain": "ai_infra"}) == ""
    assert canonical_identity_key({"source_type": "source_profile"}) == ""


def test_classify_candidate_recomputes_noncanonical_identity_when_source_fields_exist() -> None:
    result = classify_candidate(_high_value_candidate(identity_key="raw-sha256:abcdef"))

    assert result["identity_key"] == "github-repo:kserve/kserve"

    typed = classify_candidate(
        _high_value_candidate(
            source_type="github_repo",
            url="https://github.com/kserve/kserve",
            identity_key="raw-sha256:abcdef",
        )
    )
    assert typed["identity_key"] == "github-repo:kserve/kserve"

    invalid_only = classify_candidate(
        {
            "identity_key": "github:kserve/kserve",
            "candidate_id": "project:kserve",
            "decision_inputs": {
                "source_type_count": 2,
                "local_gap_level": "major",
                "duplicate_status": "none",
                "acquisition_path": "github_backfill",
            },
            "hard_gates": {
                "has_gap_proof": True,
                "has_two_source_types_for_deep_dive": True,
                "has_evaluator_scenario": True,
                "has_domain_channel_plan": True,
                "has_depth_acquisition_proof": True,
                "identity_key_is_canonical": True,
            },
            "priority_score": 99,
        }
    )
    assert invalid_only["classification"] != "high_value"
    assert "identity_key" in invalid_only["missing_inputs"]

    invalid_issue = classify_candidate(
        _high_value_candidate(
            url="",
            source_type="github_issue",
            owner="kserve",
            repo="kserve",
            issue_number="abc",
        )
    )
    assert invalid_issue["classification"] != "high_value"
    assert "identity_key" in invalid_issue["missing_inputs"]

    invalid_raw = classify_candidate(
        {
            "raw_sha256": "not-a-hex-digest",
            "decision_inputs": {
                "source_type_count": 2,
                "local_gap_level": "major",
                "duplicate_status": "none",
                "acquisition_path": "existing_raw",
            },
            "hard_gates": {
                "has_gap_proof": True,
                "has_two_source_types_for_deep_dive": True,
                "has_evaluator_scenario": True,
                "has_domain_channel_plan": True,
                "has_depth_acquisition_proof": True,
                "identity_key_is_canonical": True,
            },
        }
    )
    assert invalid_raw["classification"] != "high_value"
    assert "identity_key" in invalid_raw["missing_inputs"]


def _governance_p0_payloads() -> dict[str, object]:
    candidate = _high_value_candidate()
    classification = classify_candidate(candidate)
    return {
        "egress": {
            "probes": [
                {
                    "probe_url": "https://api.github.com",
                    "started_at": "2026-07-08T00:00:00Z",
                    "finished_at": "2026-07-08T00:00:01Z",
                    "dns_status": "ok",
                    "tls_status": "ok",
                    "http_status": 200,
                    "final_url": "https://api.github.com/",
                    "error_class": "",
                    "summary": "GitHub API reachable",
                }
            ]
        },
        "identity": {
            "status": "pass",
            "candidates": [
                {
                    "candidate_id": "project:kserve",
                    "candidate": candidate,
                    "identity_key": classification["identity_key"],
                }
            ],
        },
        "depth": {
            "status": "pass",
            "identity_key": classification["identity_key"],
            "acquisition_path": "github_backfill",
            "bounded": True,
            "max_items": 25,
            "source_types": ["closed_issues", "release_notes"],
            "items": [
                {"source_type": "closed_issues", "url": "https://api.github.com/repos/kserve/kserve/issues/1"},
                {"source_type": "release_notes", "url": "https://github.com/kserve/kserve/releases/tag/v0.15.0"},
            ],
        },
        "candidate_scoring": {
            "status": "pass",
            "candidate": candidate,
            "identity_key": classification["identity_key"],
            "classification": classification["classification"],
            "high_value_eligible": classification["high_value_eligible"],
        },
    }


def test_validate_governance_preflight_evidence_requires_run_local_p0_artifacts(tmp_path) -> None:
    run_dir = tmp_path / ".codex" / "loop-runs" / "ai-infra-loop-governance-dev"

    result = validate_governance_preflight_evidence(run_dir)

    assert result["status"] == "blocked"
    assert result["next_action"] == "collect_governance_preflight_evidence"
    assert ".codex/loop-runs/ai-infra-loop-governance-dev/egress-proof.json" in result["missing_artifacts"]
    assert ".codex/loop-runs/ai-infra-loop-governance-dev/identity-key-audit.json" in result["missing_artifacts"]
    assert ".codex/loop-runs/ai-infra-loop-governance-dev/depth-acquisition-smoke.json" in result["missing_artifacts"]
    assert ".codex/loop-runs/ai-infra-loop-governance-dev/candidate-scoring/*.json" in result["missing_artifacts"]
    assert "P0 governance preflight artifacts" in result["reader_summary"]["next_step"]


def test_validate_governance_preflight_evidence_uses_canonical_candidate_scoring(tmp_path) -> None:
    run_dir = tmp_path / ".codex" / "loop-runs" / "ai-infra-loop-governance-dev"
    scoring_dir = run_dir / "candidate-scoring"
    scoring_dir.mkdir(parents=True)
    payloads = _governance_p0_payloads()
    (run_dir / "egress-proof.json").write_text(json_dumps(payloads["egress"]), encoding="utf-8")
    (run_dir / "identity-key-audit.json").write_text(json_dumps(payloads["identity"]), encoding="utf-8")
    (run_dir / "depth-acquisition-smoke.json").write_text(json_dumps(payloads["depth"]), encoding="utf-8")
    tampered_scoring = {
        **payloads["candidate_scoring"],
        "classification": "high_value",
        "candidate": {
            **_high_value_candidate(),
            "hard_gates": {
                **_high_value_candidate()["hard_gates"],
                "has_depth_acquisition_proof": False,
            },
        },
    }
    (scoring_dir / "candidate-001.json").write_text(json_dumps(tampered_scoring), encoding="utf-8")

    blocked = validate_governance_preflight_evidence(run_dir)

    assert blocked["status"] == "blocked"
    assert any("classification high_value does not match computed" in finding for finding in blocked["findings"])

    (scoring_dir / "candidate-001.json").write_text(json_dumps(payloads["candidate_scoring"]), encoding="utf-8")
    passing = validate_governance_preflight_evidence(run_dir)

    assert passing["status"] == "pass"
    assert passing["findings"] == []
    assert (
        ".codex/loop-runs/ai-infra-loop-governance-dev/candidate-scoring/candidate-001.json"
        in passing["artifact_paths"]
    )


def json_dumps(payload: object) -> str:
    import json

    return json.dumps(payload, indent=2) + "\n"
