import unittest

from scripts.harness_ai_infra_evidence import (
    canonicalize_url,
    identity_key_for_candidate,
    validate_gap_proof_payload,
)


class HarnessAiInfraEvidenceTests(unittest.TestCase):
    def test_canonicalize_url_normalizes_tracking_noise_and_case(self) -> None:
        self.assertEqual(
            canonicalize_url("HTTPS://Docs.VLLM.AI/en/latest/foo/?utm_source=x#section"),
            "https://docs.vllm.ai/en/latest/foo/#section",
        )

    def test_identity_key_for_candidate_normalizes_supported_sources(self) -> None:
        self.assertEqual(
            identity_key_for_candidate(
                {
                    "source_type": "github_issue",
                    "owner": "kubernetes",
                    "repo": "kubernetes",
                    "number": 123,
                }
            ),
            "github:kubernetes/kubernetes#123",
        )
        self.assertEqual(
            identity_key_for_candidate({"source_type": "paper", "arxiv_id": "2401.01234v2"}),
            "arxiv:2401.01234",
        )
        self.assertEqual(
            identity_key_for_candidate(
                {
                    "source_type": "hardware",
                    "vendor": "NVIDIA",
                    "model": "H200 SXM",
                    "sku_or_memory_variant": "141GB",
                }
            ),
            "hardware:nvidia:h200-sxm:141gb",
        )

    def test_validate_gap_proof_requires_duplicate_checks(self) -> None:
        findings = validate_gap_proof_payload({})

        self.assertIn("missing task_id", findings)
        self.assertIn("missing layer", findings)
        self.assertIn("missing candidate.title", findings)
        self.assertIn("missing candidate.source_type", findings)
        self.assertIn("missing candidate.identity_key", findings)
        self.assertIn("missing local_checks.raw_manifest_scan", findings)
        self.assertIn("missing local_checks.wiki_search", findings)
        self.assertIn("missing local_checks.domain_index_scan", findings)
        self.assertIn("missing gap_reason", findings)
        self.assertIn("planned_outputs must be a non-empty list", findings)
