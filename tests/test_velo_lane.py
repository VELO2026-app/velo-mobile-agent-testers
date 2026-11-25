"""Our lane: signing, the key preflight, the workflow's secret hygiene, personas."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import unittest
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "velo"))
import sign_init_data as sid  # noqa: E402

WORKFLOW = (ROOT / ".github" / "workflows" / "velo-android.yml").read_text(encoding="utf-8")


def parse_init(data: str) -> dict:
    return {k: urllib.parse.unquote(v) for k, v in (p.split("=", 1) for p in data.split("&"))}


class SignTest(unittest.TestCase):
    def test_signature_is_telegrams(self):
        data = sid.build_init_data({"id": 610001, "first_name": "Ольга"}, "e2e:fake", now=1_700_000_000, query_id="q1")
        p = parse_init(data)
        got = p.pop("hash")
        check = "\n".join(f"{k}={p[k]}" for k in sorted(p))
        secret = hmac.new(b"WebAppData", b"e2e:fake", hashlib.sha256).digest()
        self.assertEqual(got, hmac.new(secret, check.encode(), hashlib.sha256).hexdigest())
        self.assertEqual(json.loads(p["user"])["first_name"], "Ольга")

    def test_each_call_is_unique(self):
        a = parse_init(sid.build_init_data({"id": 1, "first_name": "x"}, "e2e:fake"))
        b = parse_init(sid.build_init_data({"id": 1, "first_name": "x"}, "e2e:fake"))
        self.assertNotEqual(a["query_id"], b["query_id"])

    def test_launch_url_carries_telegram_params_in_the_hash(self):
        url = sid.launch_url("a=b&hash=c", "http://localhost:4173/", "/user/diary")
        self.assertTrue(url.startswith("http://localhost:4173/user/diary#tgWebAppData="))
        frag = urllib.parse.parse_qs(url.split("#", 1)[1])
        self.assertEqual(frag["tgWebAppData"], ["a=b&hash=c"])
        self.assertEqual(frag["tgWebAppPlatform"], ["android"])

    def run_cli(self, token: str):
        env = {**os.environ, "TELEGRAM_BOT_TOKEN": token}
        return subprocess.run([sys.executable, str(ROOT / "scripts/velo/sign_init_data.py"), "data", "--id", "610001"],
                              capture_output=True, text=True, env=env)

    def test_fake_token_is_accepted_real_looking_is_refused(self):
        self.assertEqual(self.run_cli("e2e:fake").returncode, 0)
        r = self.run_cli("123456789:AAH" + "x" * 32)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("refusing", r.stderr)
        self.assertNotIn("AAH", r.stderr + r.stdout)  # never echoed


class PreflightTest(unittest.TestCase):
    def run_pf(self, **env):
        base = {"PATH": os.environ["PATH"], "GITHUB_REPOSITORY": "o/r"}
        return subprocess.run(["bash", str(ROOT / "scripts/velo/preflight.sh")], cwd=ROOT,
                              capture_output=True, text=True, env={**base, **env})

    def test_no_key_fails_with_instructions(self):
        r = self.run_pf(AGENT="true")
        self.assertEqual(r.returncode, 1)
        self.assertIn("::error", r.stdout)
        for must in ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY", "gh secret set", "agent=false"):
            self.assertIn(must, r.stdout + r.stderr)

    def test_dry_run_needs_no_key(self):
        self.assertEqual(self.run_pf(AGENT="false").returncode, 0)

    def test_any_known_key_passes_and_is_not_echoed(self):
        for name in ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY"):
            r = self.run_pf(AGENT="true", **{name: "sk" + "-ant-" + "secretvalue123456"})
            self.assertEqual(r.returncode, 0, name)
            self.assertNotIn("secretvalue", r.stdout + r.stderr)

    def test_other_api_needs_its_own_key(self):
        self.assertEqual(self.run_pf(AGENT="true", LLM_BASE_URL="https://x.test/api").returncode, 1)
        self.assertEqual(self.run_pf(AGENT="true", LLM_BASE_URL="https://x.test/api", LLM_API_KEY="k").returncode, 0)


class WorkflowTest(unittest.TestCase):
    def test_secrets_appear_only_where_intended(self):
        refs = re.findall(r"secrets\.([A-Z_]+)", WORKFLOW)
        self.assertEqual(sorted(set(refs)), ["ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "LLM_API_KEY"])
        # twice each: the key check of the plan job and the agent's emulator step
        for name in set(refs):
            self.assertEqual(refs.count(name), 2, name)

    def test_job_level_env_has_no_secret_and_the_bot_token_is_fake(self):
        job_env = WORKFLOW.split("\n  android:", 1)[1].split("\n    env:\n", 1)[1].split("    steps:", 1)[0]
        self.assertNotIn("secrets.", job_env)
        self.assertIn("TELEGRAM_BOT_TOKEN: 'e2e:fake'", job_env)

    def test_permissions_are_read_only(self):
        self.assertIn("permissions:\n  contents: read", WORKFLOW)
        self.assertNotRegex(WORKFLOW, r"pull_request_target|permissions:\s*\n\s*(contents|id-token): write")

    def test_trigger_is_manual_only(self):
        on = WORKFLOW.split("on:\n", 1)[1].split("\npermissions:", 1)[0]
        self.assertIn("workflow_dispatch:", on)
        self.assertNotRegex(on, r"\n  (push|pull_request|schedule):")


class PersonasTest(unittest.TestCase):
    def test_android_only_and_complete(self):
        personas = json.loads((ROOT / "personas.json").read_text(encoding="utf-8"))
        self.assertEqual({p["platform"] for p in personas}, {"android"})
        ids = {p["id"] for p in personas}
        self.assertTrue({"malik", "anna"} <= ids)

    def test_matrix_rows(self):
        env = {**os.environ, "PERSONAS": "malik,anna", "PLATFORM": "android"}
        out = subprocess.run([sys.executable, str(ROOT / "scripts/matrix.py")], cwd=ROOT, capture_output=True,
                             text=True, env=env, check=True).stdout
        rows = json.loads(out.split("=", 1)[1])
        self.assertEqual([r["persona"] for r in rows], ["malik", "anna"])
        self.assertTrue(all({"profile", "api", "font_scale", "theme", "locale", "geo", "device"} <= set(r) for r in rows))


if __name__ == "__main__":
    unittest.main()


class ChromeReadyTest(unittest.TestCase):
    """Only Chrome's native dialog buttons are pressed, never the page's own."""

    def node(self, text, rid, bounds="[0,0][100,100]"):
        import xml.etree.ElementTree as ET
        return ET.Element("node", {"text": text, "resource-id": rid, "bounds": bounds})

    def run_with(self, rounds):
        import chrome_ready
        taps, seq = [], iter(rounds)
        chrome_ready.ui_nodes = lambda: next(seq, [])
        orig = chrome_ready.adb
        chrome_ready.adb = lambda *a, **k: taps.append(a) or ""
        chrome_ready.time.sleep = lambda s: None
        try:
            return chrome_ready.dismiss_prompts(), [t for t in taps if t[:3] == ("shell", "input", "tap")]
        finally:
            chrome_ready.adb = orig

    def test_native_decline_button_is_tapped(self):
        closed, taps = self.run_with([[self.node("No thanks", "com.android.chrome:id/negative_button", "[0,0][200,100]")], []])
        self.assertEqual(closed, ["No thanks"])
        self.assertEqual(taps, [("shell", "input", "tap", "100", "50")])

    def test_the_apps_own_button_with_the_same_word_is_left_alone(self):
        closed, taps = self.run_with([[self.node("Skip", "")], [self.node("Skip", "")], []])
        self.assertEqual((closed, taps), ([], []))


class TelegramProbeTest(unittest.TestCase):
    """The probe must stay keyless and loginless."""

    text = (ROOT / ".github/workflows/telegram-probe.yml").read_text(encoding="utf-8")
    scripts = (ROOT / "scripts/telegram/probe.sh").read_text(encoding="utf-8") + \
        (ROOT / "scripts/telegram/probe.py").read_text(encoding="utf-8")

    def test_no_secrets_and_manual_only(self):
        self.assertNotIn("secrets.", self.text)
        self.assertIn("workflow_dispatch:", self.text)
        self.assertNotRegex(self.text, r"\n  (push|pull_request|schedule):")

    def test_never_types_or_enters_a_number(self):
        self.assertNotRegex(self.scripts, r"input\s*['\"]?,?\s*['\"]?text|type\.py|\"text\"")
        self.assertNotRegex(self.scripts, r"9996|\+\d{6,}")
