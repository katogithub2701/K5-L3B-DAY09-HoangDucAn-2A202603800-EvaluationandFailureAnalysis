"""M1/M3 regression: ticket_trust (FM-03) must fail on seeded_regression and pass on fixed.

Run: python -m pytest -q -m student -o addopts= -k lab9_trace_case
"""
import pytest

pytestmark = pytest.mark.student


def _ctx(trial, label):
    from pydantic_evals.evaluators import EvaluatorContext

    return EvaluatorContext(name="c-002@11", inputs={}, metadata=None, expected_output=label,
                            output=trial, duration=0.0, _span_tree=None, attributes={}, metrics={})


def test_c002_ticket_trust_first_wrong_step():
    from lab9 import graders, trace_case

    bad = trace_case.investigate("seeded_regression", "C-002", 11)
    good = trace_case.investigate("fixed", "C-002", 11)

    # FM-03: the defect appears at the model_override event, before the quote.
    overrides = [e for e in bad["trial"]["events"] if e.get("kind") == "model_override"]
    assert overrides, "seeded_regression must leave a model_override event (FM-03)"
    first = bad["trial"]["events"].index(overrides[0]) + 1
    assert first < next(i for i, e in enumerate(bad["trial"]["events"], 1) if e.get("kind") == "quote")

    assert graders.DbFactKept().evaluate(_ctx(bad["trial"], bad["label"])).value is False
    assert graders.DbFactKept().evaluate(_ctx(good["trial"], good["label"])).value is True
    assert bad["trial"]["lab8_pass"] is False
    assert good["trial"]["lab8_pass"] is True


def test_item_e002_carries_fm03():
    import json
    from pathlib import Path

    items = [json.loads(line) for line in Path("data/eval/eval_set_v1.jsonl").read_text(encoding="utf-8").splitlines()
             if line.strip()]
    item = next(i for i in items if i["claim_id"] == "C-002")
    assert "FM-03" in item["failure_modes"]
