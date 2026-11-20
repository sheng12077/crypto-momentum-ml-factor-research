from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_early_weekly_universe as weekly  # noqa: E402


def stamp(text):
    return int(datetime.fromisoformat(text + "T00:00:00+00:00").timestamp() * 1000)


def identity(symbol="BTCUSDT", pending=False):
    rule = {
        "instrument_id": symbol,
        "vendor_asset_id": 1,
        "scope_from": "2020-01-06T00:00:00+00:00",
        "scope_to_exclusive": "2020-01-13T00:00:00+00:00",
        "size_identity_join_allowed": not pending,
        "pending_gates": ["venue_futures"] if pending else [],
        "proof_checks": {
            "historical_identity": True,
            "provider_identity": True,
            "venue_name": True,
            "token_contract": True,
            "venue_futures": not pending,
        },
        "usd_market_cap_scale": "1",
        "price_or_history_splice_allowed": False,
        "historical_publication_vintage_proven": False,
        "historical_strategy_eligible": False,
        "funding_cashflows_verified": False,
    }
    return {
        "instrument_id": symbol,
        "identity_status": "pending_registered_evidence" if pending else "corroborated_identity",
        "mapping_record": {
            "mapping": rule,
            "rule_sha256": weekly.fingerprint(rule),
            "provenance": "old",
        },
        "missing_requirements": rule["pending_gates"],
        "strict_strategy_eligible": False,
    }


def observation(reference, symbol="BTCUSDT", **changes):
    result = {
        "instrument_id": symbol,
        "reference_time_ms": reference,
        "data_day": (
            datetime.fromtimestamp(reference / 1000, UTC).date() - timedelta(days=1)
        ).isoformat(),
        "price_history_diagnostic_candidate": True,
        "valid_closing_observation": True,
        "complete_trade_day": True,
        "known_composite_index": False,
        "audit_at_or_after_confirmed_settlement": False,
        "funding_freshness_diagnostic": True,
    }
    return result | changes


class EarlyWeeklyTests(unittest.TestCase):
    def test_scope_start_inclusive_stop_exclusive(self):
        a = identity()
        for day, expected in [
            ("2020-01-05", False),
            ("2020-01-06", True),
            ("2020-01-12", True),
            ("2020-01-13", False),
        ]:
            t = stamp(day)
            self.assertEqual(
                weekly.week_row(a, observation(t), t)["identity_scope_history_candidate"], expected
            )

    def test_freshness_does_not_change_identity_or_claim_paid_funding(self):
        t = stamp("2020-01-06")
        result = weekly.week_row(identity(), observation(t, funding_freshness_diagnostic=False), t)
        self.assertTrue(result["identity_scope_history_candidate"])
        self.assertFalse(result["identity_scope_history_with_fresh_funding"])
        self.assertEqual(result["funding_exclusion"], "missing_or_stale_funding")
        self.assertFalse(result["strict_trading_eligibility_established"])

    def test_settlement_index_missing_close_and_pending_identity_excluded(self):
        t = stamp("2020-01-06")
        for changes in [
            {"known_composite_index": True},
            {"audit_at_or_after_confirmed_settlement": True},
            {"valid_closing_observation": False},
            {"complete_trade_day": False},
            {"price_history_diagnostic_candidate": False},
        ]:
            row = weekly.week_row(identity(), observation(t, **changes), t)
            self.assertFalse(row["identity_scope_history_candidate"])
            self.assertTrue(row["identity_history_exclusion_reasons"])
        self.assertFalse(
            weekly.week_row(identity(pending=True), observation(t), t)[
                "identity_scope_history_candidate"
            ]
        )

    def test_weekly_members_and_primary_reasons_reconcile(self):
        times = [stamp("2020-01-06"), stamp("2020-01-13")]
        a, b = identity(), identity("ETHUSDT", True)
        panel = {s: {t: observation(t, s) for t in times} for s in ["BTCUSDT", "ETHUSDT"]}
        detail, weeks = weekly.coverage(panel, [a, b], times)
        self.assertEqual(len(detail), 4)
        self.assertEqual(weeks[0]["price_history_candidate_count"], 2)
        self.assertEqual(weeks[0]["identity_scope_history_candidate_members"], ["BTCUSDT"])
        self.assertEqual(weeks[1]["identity_scope_history_candidate_count"], 0)
        self.assertEqual(sum(weeks[1]["primary_identity_history_exclusion_counts"].values()), 2)
        stats = weekly.stats(weeks, "identity_scope_history_candidate")
        self.assertEqual(stats["minimum"], 0)
        self.assertEqual(stats["median"], 0.5)
        self.assertEqual(stats["first_nonempty_week"], "2020-01-06")
        with self.assertRaisesRegex(ValueError, "calendar"):
            weekly.coverage({"BTCUSDT": {times[0]: panel["BTCUSDT"][times[0]]}}, [a], times)

    def test_btc_replacement_preserves_other_records_and_limitations(self):
        old = [identity(pending=True), identity("ETHUSDT")]
        snapshot = copy.deepcopy(old)
        rows = weekly.integrate_btc(old, old[0]["mapping_record"]["rule_sha256"], "audit")
        self.assertEqual(old, snapshot)
        self.assertEqual(rows[1], old[1])
        self.assertEqual(rows[0]["mapping_record"]["superseded"], old[0]["mapping_record"])
        rule = rows[0]["mapping_record"]["mapping"]
        self.assertTrue(rule["size_identity_join_allowed"])
        for key in [
            "scope_from",
            "scope_to_exclusive",
            "usd_market_cap_scale",
            "price_or_history_splice_allowed",
            "historical_publication_vintage_proven",
            "historical_strategy_eligible",
            "funding_cashflows_verified",
        ]:
            self.assertEqual(rule[key], old[0]["mapping_record"]["mapping"][key])
        with self.assertRaisesRegex(ValueError, "predecessor"):
            weekly.integrate_btc(old, "wrong", "audit")

    def test_positive_summary_alone_cannot_approve_failed_evidence(self):
        rule = identity(pending=True)["mapping_record"]["mapping"]
        summary = {
            "success": True,
            "sampled_cross_check_passed": True,
            "combined_identity_evidence_satisfied": True,
        }
        article = {"clauses_verified": True}
        assessment = {
            "combined_identity_evidence_satisfied": True,
            "dated_2019_notice": article,
            "prior_identity_checks": rule["proof_checks"],
            "scope_from": rule["scope_from"],
            "scope_to_exclusive": rule["scope_to_exclusive"],
        }
        checks = {str(i): {"passed": True} for i in range(7)}
        weekly.require_btc_proofs(summary, checks, assessment, article, rule)
        for changed in [
            checks | {"0": {"passed": False}},
            {},
            checks | {"eighth": {"passed": True}},
        ]:
            with self.assertRaisesRegex(ValueError, "evidence inconsistent"):
                weekly.require_btc_proofs(summary, changed, assessment, article, rule)
        with self.assertRaisesRegex(ValueError, "evidence inconsistent"):
            weekly.require_btc_proofs(
                summary, checks, assessment | {"scope_from": "2020-01-01"}, article, rule
            )

    def test_wrong_previous_day_and_tool_tampering_rejected(self):
        t = stamp("2020-01-06")
        with self.assertRaisesRegex(ValueError, "previous UTC day"):
            weekly.week_row(identity(), observation(t, data_day="2020-01-06"), t)
        with tempfile.TemporaryDirectory() as folder, patch.object(weekly, "ROOT", Path(folder)):
            p = Path(folder) / "scripts/tool.py"
            p.parent.mkdir()
            p.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "tool changed"):
                weekly.verify_tool({"script_sha256": weekly.digest(b"original")}, "tool.py")
