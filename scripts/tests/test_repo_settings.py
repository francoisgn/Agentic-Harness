"""Tests de scripts/repo-settings.py : calcul des changements (pur) et application (HTTP simulé)."""
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("repo_settings", ROOT / "scripts" / "repo-settings.py")
rs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rs)

RULESET = {"name": "master protégée", "target": "branch", "enforcement": "active",
           "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
           "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}]}


class PlanTests(unittest.TestCase):
    def test_nothing_to_do_when_aligned(self):
        desired = {"repository": {"description": "x", "has_wiki": False}, "topics": ["b", "a"], "rulesets": []}
        current = {"repository": {"description": "x", "has_wiki": False, "name": "r"}, "topics": ["a", "b"], "rulesets": []}
        self.assertEqual(rs.plan(desired, current), [])

    def test_repository_fields_only_changed_ones(self):
        actions = rs.plan({"repository": {"description": "nouvelle", "has_wiki": False}},
                          {"repository": {"description": "ancienne", "has_wiki": False}, "topics": [], "rulesets": []})
        self.assertEqual(actions, [{"op": "patch-repo", "fields": {"description": "nouvelle"}}])

    def test_topics_replaced_as_a_set(self):
        actions = rs.plan({"topics": ["claude-code", "agentic"]}, {"repository": {}, "topics": ["old"], "rulesets": []})
        self.assertEqual(actions, [{"op": "put-topics", "names": ["agentic", "claude-code"]}])

    def test_placeholder_description_is_never_sent(self):
        desired = {"repository": {"description": "<une phrase : ce que fait le projet, pour qui>", "has_wiki": False}}
        actions = rs.plan(desired, {"repository": {"description": "", "has_wiki": True}, "topics": [], "rulesets": []})
        self.assertEqual(actions, [{"op": "patch-repo", "fields": {"has_wiki": False}}])

    def test_identity_gaps_none_when_described_and_tagged(self):
        self.assertEqual(rs.identity_gaps({"repository": {"description": "Un cadre."}, "topics": ["ai-agents", "tdd"]}), [])

    def test_identity_gaps_on_missing_or_placeholder_description(self):
        for repo in ({}, {"description": ""}, {"description": "<une phrase>"}):
            gaps = rs.identity_gaps({"repository": repo, "topics": ["tdd"]})
            self.assertEqual(len(gaps), 1, repo)
            self.assertIn("description", gaps[0])

    def test_identity_gaps_on_empty_or_invalid_topics(self):
        ok = {"description": "Un cadre."}
        self.assertIn("topics", rs.identity_gaps({"repository": ok, "topics": []})[0])
        self.assertIn("topics", rs.identity_gaps({"repository": ok})[0])
        for bad in ("Claude Code", "CI", "-tdd", "x" * 51):
            self.assertIn(bad, rs.identity_gaps({"repository": ok, "topics": ["tdd", bad]})[0])
        self.assertIn("20", rs.identity_gaps({"repository": ok, "topics": [f"t{i}" for i in range(21)]})[0])

    def test_shipped_settings_have_description_and_topics(self):
        shipped = json.loads((ROOT / ".github/repo-settings.json").read_text(encoding="utf-8"))
        self.assertEqual(rs.identity_gaps(shipped), [])

    def test_ruleset_created_then_updated_by_name(self):
        created = rs.plan({"rulesets": [RULESET]}, {"repository": {}, "topics": [], "rulesets": []})
        self.assertEqual([a["op"] for a in created], ["create-ruleset"])
        current = dict(RULESET, id=42, rules=[{"type": "deletion"}])
        updated = rs.plan({"rulesets": [RULESET]}, {"repository": {}, "topics": [], "rulesets": [current]})
        self.assertEqual([(a["op"], a.get("id")) for a in updated], [("update-ruleset", 42)])
        same = rs.plan({"rulesets": [RULESET]}, {"repository": {}, "topics": [],
                                                  "rulesets": [dict(RULESET, id=42, source="o/r", node_id="n")]})
        self.assertEqual(same, [])

    def test_api_defaults_absent_from_file_do_not_cause_updates(self):
        desired = {"rulesets": [{"name": "p", "target": "branch", "enforcement": "active",
                                 "rules": [{"type": "pull_request", "parameters": {"required_approving_review_count": 0}},
                                           {"type": "required_status_checks", "parameters": {
                                               "required_status_checks": [{"context": "CI"}]}}]}]}
        api = {"id": 9, "name": "p", "target": "branch", "enforcement": "active", "source_type": "Repository",
               "rules": [{"type": "required_status_checks", "parameters": {
                             "do_not_enforce_on_create": False,
                             "required_status_checks": [{"context": "CI", "integration_id": 15368}]}},
                         {"type": "pull_request", "parameters": {"required_approving_review_count": 0,
                                                                 "allowed_merge_methods": ["merge", "squash"]}}]}
        self.assertEqual(rs.plan(desired, {"repository": {}, "topics": [], "rulesets": [api]}), [])

    def test_extra_rule_in_github_or_changed_value_triggers_update(self):
        desired = {"rulesets": [{"name": "p", "rules": [{"type": "deletion"}]}]}
        extra = {"id": 9, "name": "p", "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}]}
        changed = {"id": 9, "name": "p", "rules": [{"type": "creation"}]}
        for cur in (extra, changed):
            self.assertEqual([a["op"] for a in rs.plan(desired, {"repository": {}, "topics": [], "rulesets": [cur]})],
                             ["update-ruleset"])

    def test_bypass_added_by_hand_is_a_drift_when_file_declares_none(self):
        desired = {"rulesets": [{"name": "p", "bypass_actors": [], "rules": [{"type": "deletion"}]}]}
        hand = {"id": 9, "name": "p", "rules": [{"type": "deletion"}],
                "bypass_actors": [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}]}
        self.assertEqual([a["op"] for a in rs.plan(desired, {"repository": {}, "topics": [], "rulesets": [hand]})],
                         ["update-ruleset"])

    def test_shipped_settings_declare_no_bypass(self):
        for p in (ROOT / ".github/repo-settings.json", ROOT / "templates/.github/repo-settings.json"):
            for ruleset in json.loads(p.read_text(encoding="utf-8"))["rulesets"]:
                self.assertEqual(ruleset.get("bypass_actors"), [], p)

    def test_duplicate_ruleset_names_are_rejected(self):
        with self.assertRaises(ValueError):
            rs.plan({"rulesets": [{"name": "p"}, {"name": "p"}]}, {"repository": {}, "topics": [], "rulesets": []})

    def test_current_without_repository_key(self):
        self.assertEqual(rs.plan({"repository": {"description": "d"}}, {})[0]["op"], "patch-repo")

    def test_unmanaged_rulesets_are_never_deleted(self):
        current = {"repository": {}, "topics": [], "rulesets": [dict(RULESET, id=7, name="à la main")]}
        self.assertEqual(rs.plan({"rulesets": []}, current), [])

    def test_absent_sections_are_left_alone(self):
        self.assertEqual(rs.plan({}, {"repository": {"description": "x"}, "topics": ["a"], "rulesets": []}), [])

    def test_unknown_section_is_rejected_but_comments_allowed(self):
        empty = {"repository": {}, "topics": [], "rulesets": []}
        with self.assertRaises(ValueError):
            rs.plan({"ruleset": []}, empty)  # faute de frappe : sinon ignorée en silence
        self.assertEqual(rs.plan({"$comment": "doc"}, empty), [])

    def test_unknown_repository_field_is_rejected(self):
        with self.assertRaises(ValueError):
            rs.plan({"repository": {"visibility": "public"}}, {"repository": {}, "topics": [], "rulesets": []})


class ApplyTests(unittest.TestCase):
    def test_apply_sends_expected_requests(self):
        sent = []

        def http(method, path, body=None):
            sent.append((method, path, body))
            return {}
        actions = [{"op": "patch-repo", "fields": {"description": "d"}},
                   {"op": "put-topics", "names": ["a"]},
                   {"op": "create-ruleset", "ruleset": RULESET},
                   {"op": "update-ruleset", "id": 42, "ruleset": RULESET}]
        rs.apply("o/r", actions, http)
        self.assertEqual([(m, p) for m, p, _ in sent], [("PATCH", "/repos/o/r"), ("PUT", "/repos/o/r/topics"),
                                                        ("POST", "/repos/o/r/rulesets"), ("PUT", "/repos/o/r/rulesets/42")])
        self.assertEqual(sent[1][2], {"names": ["a"]})

    def test_read_current_fetches_full_rulesets(self):
        def http(method, path, body=None):
            return {"/repos/o/r": {"description": "d"}, "/repos/o/r/topics": {"names": ["a"]},
                    "/repos/o/r/rulesets?includes_parents=false": [{"id": 1, "name": "x"}],
                    "/repos/o/r/rulesets/1": dict(RULESET, id=1)}[path]
        cur = rs.read_current("o/r", http)
        self.assertEqual((cur["topics"], cur["rulesets"][0]["rules"]), (["a"], RULESET["rules"]))


class ShippedSettingsTests(unittest.TestCase):
    def test_framework_and_template_settings_are_valid(self):
        for p in (ROOT / ".github/repo-settings.json", ROOT / "templates/.github/repo-settings.json"):
            desired = json.loads(p.read_text(encoding="utf-8"))
            rs.plan(desired, {"repository": {}, "topics": [], "rulesets": []})  # lève si un champ est inconnu


if __name__ == "__main__":
    unittest.main()
