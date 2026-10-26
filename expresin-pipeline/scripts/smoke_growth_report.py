from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
TEST_TMP = ROOT / ".deepworks" / "tmp"
TEST_TMP.mkdir(parents=True, exist_ok=True)
TEST_DATA = Path(tempfile.mkdtemp(prefix="growth-test-", dir=TEST_TMP))
os.environ["EXPRESIN_DATA_DIR"] = str(TEST_DATA)
sys.path.insert(0, str(ROOT / "expresin-pipeline" / "server"))

import app as backend  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from llm import LLMError  # noqa: E402

client = TestClient(backend.app)
checks = 0


def check(condition, message):
    global checks
    if not condition:
        raise AssertionError(message)
    checks += 1


def register(username):
    response = client.post(
        "/auth/register",
        json={"username": username, "password": "growth-test-password", "display_name": username},
    )
    check(response.status_code == 201, f"register {username}: {response.text}")
    body = response.json()
    return body["user"], {"Authorization": f"Bearer {body['token']}"}


def create_experiment(experiment_id, owner_id, title):
    processed = {
        "metadata": {
            "01_Metadata": {
                "objective": {"label": "实验目的", "value": "比较两种树脂的吸附表现", "unit": None},
                "reviewer": {"label": "复核人", "value": "实验员本人", "unit": None},
            }
        },
        "provenance": {
            "01_Metadata.objective": {"status": "confirmed", "source_type": "manual"},
        },
        "recognized_data": {
            "regions": [{"blocks": [{"columns": [{"conf": 0.93, "target": "signal_area"}]}]}],
        },
        "canonical": {
            "rows": [
                {"analyte": "Ca", "sample_number": 1, "conc_ppm_computed": 10.0},
                {"analyte": "Ca", "sample_number": 2, "conc_ppm_computed": 8.5},
            ],
            "calculations": [{"type": "calibration_fit", "ok": True, "fit": {"r2": 0.999}}],
            "verification": [],
            "summary": {"n": 2, "mean_relative_deviation": 0.01},
            "assumptions": [],
            "notes": [],
        },
    }
    return backend.store.create_experiment(
        experiment_id=experiment_id,
        session_id=f"sess-{experiment_id}",
        project_id="GROWTH_TEST",
        title=title,
        experiment_type="batch",
        operator=owner_id,
        date_start="2026-10-20",
        meta=processed["metadata"],
        processed=processed,
        raw_file="raw.xlsx",
        raw_sha256="test-sha",
        owner_user_id=owner_id,
    )


class FakeLLM:
    def __init__(self):
        self.prompts = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def chat_json(self, messages, **kwargs):
        prompt = messages[1]["content"]
        self.prompts.append(prompt)
        experiment_ids = list(dict.fromkeys(re.findall(r'"experiment_id":"(RES-[^"]+)"', prompt)))
        result = {
            "summary": "实验记录逐步完整，复核习惯已形成，但仍需加强结果解释。",
            "strengths": ["能够保留实验目的与复核信息"],
            "timeline": [
                {
                    "experiment_id": experiment_id,
                    "direction": "progress",
                    "observation": "本次记录体现了更完整的实验准备与复核意识。",
                    "evidence": "归档包含实验目的、复核状态和规范数据行。",
                }
                for experiment_id in experiment_ids
            ],
            "goals": [
                {
                    "title": "提高结果解释能力",
                    "action": "每次归档后补充一段结果与实验目的的对应分析。",
                    "metric": "下一次档案包含明确的结果解释和偏差讨论。",
                    "timeframe": "两周",
                }
            ],
            "data_gaps": [],
        }
        return result, SimpleNamespace(model="fake-growth-model")


alice, alice_headers = register("alice_growth")
bob, bob_headers = register("bob_growth")
empty, empty_headers = register("empty_growth")
create_experiment("RES-ALICE-001", alice["id"], "ALICE 批次实验")
create_experiment("RES-BOB-SECRET", bob["id"], "BOB_PRIVATE_TITLE")

fake = FakeLLM()
backend.llm_client = lambda: fake

response = client.post("/v1/growth-reports", headers=empty_headers, json={})
check(response.status_code == 400, "empty account must return 400")
response = client.post("/v1/growth-reports", json={})
check(response.status_code == 401, "missing token must return 401")

response = client.post(
    "/v1/growth-reports", headers=alice_headers, json={"focus": "提高数据复核能力", "limit": 20}
)
check(response.status_code == 200, f"alice report: {response.text}")
report = response.json()
check(report["summary"] and len(report["goals"]) == 1, "summary/goals missing")
check([item["experiment_id"] for item in report["timeline"]] == ["RES-ALICE-001"], "alice timeline leaked")
check(report["statistics"]["canonical_row_count"] == 2, "deterministic statistics mismatch")
check("RES-BOB-SECRET" not in fake.prompts[-1] and "BOB_PRIVATE_TITLE" not in fake.prompts[-1], "bob data leaked")
check("提高数据复核能力" in fake.prompts[-1], "focus not forwarded")
check(report["model"]["name"] == "fake-growth-model", "model metadata missing")

admin = backend.store.get_admin()
admin_headers = {"Authorization": f"Bearer {backend.auth.issue_token(backend.store, admin['id'])}"}
create_experiment("RES-ADMIN-001", admin["id"], "ADMIN 自己的实验")
response = client.post("/v1/growth-reports", headers=admin_headers, json={})
check(response.status_code == 200, f"admin report: {response.text}")
check([item["experiment_id"] for item in response.json()["timeline"]] == ["RES-ADMIN-001"], "admin timeline mixed users")
check(
    "RES-ADMIN-001" in fake.prompts[-1]
    and "RES-ALICE-001" not in fake.prompts[-1]
    and "RES-BOB-SECRET" not in fake.prompts[-1],
    "admin prompt mixed users",
)


class BrokenLLM(FakeLLM):
    def chat_json(self, messages, **kwargs):
        return {"summary": "只有总结", "timeline": []}, SimpleNamespace(model="broken-model")


backend.llm_client = lambda: BrokenLLM()
response = client.post("/v1/growth-reports", headers=alice_headers, json={})
check(response.status_code == 502, "invalid model structure must return 502")


def unavailable_client():
    raise LLMError("test configuration missing")


backend.llm_client = unavailable_client
response = client.post("/v1/growth-reports", headers=alice_headers, json={})
check(response.status_code == 503, "unavailable model must return 503")

print(f"PASS: {checks} checks; isolated data: {TEST_DATA}")
