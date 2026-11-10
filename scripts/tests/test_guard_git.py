"""Tests of the guard-git.py hook: each refused form is refused, each legitimate form passes, the hook fails open."""
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
GUARD = ROOT / "plugins" / "harness" / "scripts" / "guard-git.py"
SPEC = importlib.util.spec_from_file_location("guard_git", GUARD)
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)

PROTECTED = ["main", "master", "develop", "beta"]


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True,
                   env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"})


class GuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp())
        cls.on_protected = cls.tmp / "proj"       # repository on `develop`
        cls.on_feature = cls.tmp / "proj" / "wt"  # second repository, on `fix/x`, under the first (for -C and cd)
        for repo, branch in ((cls.on_protected, "develop"), (cls.on_feature, "fix/x")):
            repo.mkdir(parents=True, exist_ok=True)
            git(repo, "init", "-q", "-b", branch)
            git(repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "--allow-empty",
                "-m", "init")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def reason(self, command, cwd=None):
        return guard.reason_for(command, PROTECTED, str(cwd or self.on_feature))

    def assertBlocked(self, command, cwd=None):
        self.assertIsNotNone(self.reason(command, cwd), f"should have been refused: {command!r}")

    def assertAllowed(self, command, cwd=None):
        self.assertIsNone(self.reason(command, cwd), f"should have passed: {command!r}")

    # --- Forced push -----------------------------------------------------------------------------------------------
    def test_force_forms_are_blocked(self):
        for command in ("git push --force origin fix/x", "git push -f origin fix/x", "git push -fu origin fix/x",
                        "git push -uf origin fix/x", "git push origin fix/x --force",
                        "git push --force-with-lease origin fix/x", "git push --force-with-lease=fix/x:abc origin fix/x",
                        "git push --force-w origin fix/x", "git push --force-if-includes --force-with-lease origin fix/x",
                        "git push origin +fix/x", "git push origin +HEAD:fix/x", "git push --mirror origin",
                        "git push --all origin", "git push --no-verify origin fix/x", "git push --no-veri origin fix/x"):
            with self.subTest(command=command):
                self.assertBlocked(command)

    def test_force_if_includes_alone_and_dry_run_pass(self):
        for command in ("git push --force-if-includes origin fix/x", "git push --dry-run --force origin main",
                        "git push -n -f origin main", "git push -nf origin +main", "git push --dry-run origin main",
                        "git push --dry-run --mirror origin", "git push --no-force-with-lease origin fix/x"):
            with self.subTest(command=command):
                self.assertAllowed(command)

    # --- Protected branches -----------------------------------------------------------------------------------------
    def test_push_to_protected_is_blocked(self):
        for command in ("git push origin develop", "git push origin HEAD:refs/heads/master", "git push origin x:main",
                        "git push origin refs/heads/beta", "git push --delete origin main", "git push -d origin main",
                        "git push origin :main", "git push origin --delete refs/heads/develop", "git push -- origin main"):
            with self.subTest(command=command):
                self.assertBlocked(command)

    def test_push_of_unprotected_branch_passes(self):
        for command in ("git push -u origin fix/x", "git push origin lot/LOT-1", "git push origin HEAD",
                        "git push", "git push origin", "git push origin :fix/old", "git push --delete origin fix/old",
                        "git push origin HEAD:feat/y", "git push origin v1.2.0", "git push --tags origin",
                        "git push -o ci.skip origin fix/x", "git push origin main-notes"):
            with self.subTest(command=command):
                self.assertAllowed(command)

    def test_current_branch_is_resolved(self):
        for command in ("git push", "git push origin", "git push origin HEAD", "git push -u origin HEAD",
                        'git push origin "$(git branch --show-current)"'):
            with self.subTest(command=command):
                self.assertBlocked(command, cwd=self.on_protected)
        self.assertAllowed("git push origin HEAD", cwd=self.on_feature)

    def test_branch_chosen_earlier_in_the_line_is_current(self):
        for command in ("git switch -c fix/y origin/develop && git push -u origin HEAD",
                        "git checkout -b lot/1 && git push", "git switch --create=feat/z && git push origin @",
                        "git switch --detach && git push origin HEAD:fix/z"):
            with self.subTest(command=command):
                self.assertAllowed(command, cwd=self.on_protected)
        for command in ("git switch main && git push", "git checkout develop && git push -u origin HEAD",
                        "git switch -c fix/y && git switch develop && git push", "git checkout x.txt && git push"):
            with self.subTest(command=command):
                self.assertBlocked(command, cwd=self.on_protected if "x.txt" in command else self.on_feature)

    def test_tags_at_sign_no_dry_run_and_wildcards(self):
        for command in ("git push --tags", "git push origin --tags", "git push origin v1.0.0"):
            with self.subTest(command=command):
                self.assertAllowed(command, cwd=self.on_protected)
        for command in ("git push origin @", "git push -u origin @"):
            with self.subTest(command=command):
                self.assertBlocked(command, cwd=self.on_protected)
        for command in ("git push -n --no-dry-run -f origin fix/x", "git push origin 'refs/heads/*:refs/heads/*'",
                        "git push origin 'refs/heads/ma*'", "gi't' push origin main", "\\git push -f origin x"):
            with self.subTest(command=command):
                self.assertBlocked(command)
        self.assertAllowed("git push origin 'refs/heads/fix/*:refs/heads/fix/*'")

    def test_git_dash_c_directory_and_cd_are_followed(self):
        self.assertAllowed("git -C wt push origin HEAD", cwd=self.on_protected)
        self.assertBlocked("git -C .. push origin HEAD", cwd=self.on_feature)
        self.assertBlocked("cd .. && git push", cwd=self.on_feature)
        self.assertAllowed("cd wt && git push", cwd=self.on_protected)

    def test_unreadable_current_branch_fails_open(self):
        outside = tempfile.mkdtemp()
        try:
            self.assertIsNone(guard.current_branch(outside))
            self.assertAllowed("git push", cwd=outside)
            self.assertAllowed("git push", cwd=os.path.join(outside, "absent"))
        finally:
            shutil.rmtree(outside)

    # --- Commit -----------------------------------------------------------------------------------------------------
    def test_commit_no_verify_is_blocked(self):
        for command in ("git commit --no-verify -m x", "git commit -n -m x", "git commit -nm x", "git commit -anm x",
                        "git -C . commit -n -m x", "git commit -m x --no-veri"):
            with self.subTest(command=command):
                self.assertBlocked(command)

    def test_commit_values_are_not_flags(self):
        for command in ("git commit -m -n", "git commit -mn", "git commit -am 'no -n here'", "git commit -m x",
                        "git commit -F - -m x", "git commit --amend --no-edit"):
            with self.subTest(command=command):
                self.assertAllowed(command)

    # --- Global options, wrappers, separators -----------------------------------------------------------------------
    def test_wrappers_and_separators_are_seen_through(self):
        for command in ("git -c core.hooksPath=/dev/null push --force origin fix/x",
                        "git -C . -c a=b push origin main", "env GIT_TRACE=1 git push -f origin fix/x",
                        "env -i git push origin main", "command git push origin main", "exec git push origin main",
                        "FOO=1 git push origin main", "bash -c 'git push --force origin fix/x'",
                        "sh -c \"git push origin main\"", "bash -lc 'cd . && git push -f'",
                        "eval git push origin main", "eval 'git push --force'", "echo x | xargs git push --force origin", "xargs -n1 git push origin main",
                        "echo x | xargs -I{} git push -f origin {}", "( git push origin main )",
                        "{ git push origin main; }", "true; git push origin main", "true && git push origin main",
                        "false || git push origin main", "true | git push origin main", "sleep 1 & git push origin main",
                        "true\ngit push origin main", "timeout 30 git push origin main", "nohup git push origin main",
                        "sudo -u bot git push origin main", "time git push origin main", "if true; then git push -f; fi",
                        "echo $(git push origin main)", "echo `git push --force`", "/usr/bin/git push origin main",
                        "git push origin main > /tmp/log 2>&1", "git push origin main 2>&1 | tail -1"):
            with self.subTest(command=command):
                self.assertBlocked(command)

    def test_mentions_and_harmless_commands_pass(self):
        for command in ("echo git push --force", "echo 'git push origin main'", "git log --grep='push --force'",
                        "grep -rn 'git push -f' docs", "git commit -m 'forbidden: git push --force on main'",
                        "command -v git", "git status && git diff", "git fetch origin main",
                        "git pull --ff-only origin main", "git push origin fix/x # then main",
                        "git push origin fix/x > /dev/null 2>&1", "git switch main",
                        "git commit -F - <<'EOF'\nTitle: the operator's\n\ngit push --force origin main\nEOF\n",
                        "git commit -m \"$(cat <<'EOF'\nTitle: the operator's (end)\n\ngit push --force origin main\nEOF\n)\""):
            with self.subTest(command=command):
                self.assertAllowed(command)

    def test_unparsable_command_uses_raw_regex(self):
        for command in ("git push --force origin fix/x 'unterminated", "git push origin main \"oops",
                        "git commit -n -m 'oops", "git push -fu origin x `oops"):
            with self.subTest(command=command):
                self.assertBlocked(command)
        self.assertAllowed("git push origin fix/x 'unterminated")
        self.assertAllowed("git push --dry-run --force origin main 'unterminated")
        self.assertBlocked("git push 'unterminated", cwd=self.on_protected)

    # --- Hook end to end --------------------------------------------------------------------------------------------
    def run_hook(self, stdin, project=None):
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project or self.on_feature)}
        return subprocess.run([sys.executable, str(GUARD)], input=stdin, capture_output=True, text=True, env=env)

    def payload(self, command, cwd=None):
        return json.dumps({"tool_input": {"command": command}, "cwd": str(cwd or self.on_feature)})

    def test_hook_blocks_with_doc_path_and_branch_advice(self):
        project = self.tmp / "consumer"
        (project / ".harness" / "docs").mkdir(parents=True, exist_ok=True)
        (project / ".harness" / "docs" / "BRANCHING-RELEASE.md").write_text("x", encoding="utf-8")
        (project / ".harness" / "config.json").write_text(
            json.dumps({"protected_branches": ["trunk"], "branch_types": ["feat", "fix"]}), encoding="utf-8")
        r = self.run_hook(self.payload("git push origin trunk"), project)
        self.assertEqual(r.returncode, 2)
        self.assertIn(".harness/docs/BRANCHING-RELEASE.md", r.stderr)
        self.assertIn("`<type>/<short-name>` branch (types: feat, fix)", r.stderr)
        self.assertNotIn("claude/", r.stderr)
        self.assertEqual(self.run_hook(self.payload("git push origin main"), project).returncode, 0)

    def test_hook_fails_open_on_malformed_input(self):
        for stdin in ("", "not json", "[]", '{"tool_input": "git push --force"}',
                      '{"tool_input": {"command": ["git", "push", "--force"]}}'):
            with self.subTest(stdin=stdin):
                self.assertEqual(self.run_hook(stdin).returncode, 0)

    def test_hook_ignores_commands_without_git(self):
        self.assertEqual(self.run_hook(self.payload("ls -la")).returncode, 0)
        self.assertEqual(self.run_hook(self.payload("git push -f origin fix/x")).returncode, 2)


if __name__ == "__main__":
    unittest.main()
