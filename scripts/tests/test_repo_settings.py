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

    def test_ruleset_created_then_updated_by_name(self):
        created = rs.plan({"rulesets": [RULESET]}, {"repository": {}, "topics": [], "rulesets": []})
        self.assertEqual([a["op"] for a in created], ["create-ruleset"])
        current = dict(RULESET, id=42, rules=[{"type": "deletion"}])
        updated = rs.plan({"rulesets": [RULESET]}, {"repository": {}, "topics": [], "rulesets": [current]})
        self.assertEqual([(a["op"], a.get("id")) for a in updated], [("update-ruleset", 42)])
        same = rs.plan({"rulesets": [RULESET]}, {"repository": {}, "topics": [],
                                                  "rulesets": [dict(RULESET, id=42, source="o/r", node_id="n")]})
        self.assertEqual(same, [])

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
