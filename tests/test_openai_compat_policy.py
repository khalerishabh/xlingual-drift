import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from agent.policies.openai_compat_policy import InfraError, OpenAICompatPolicy
from agent.react_loop import run_episode
from env.inject import FailureInjector
from eval.verifier import verify

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = json.loads((ROOT / "tasks/templates/travel_017.json").read_text(encoding="utf-8"))
CONTEXT = {"session_date": TEMPLATE["session_date"]}


def gold(h):
    return json.loads((ROOT / f"tasks/gold/travel_017_h{h}.json").read_text(encoding="utf-8"))


def call(name, args, cid, raw=None):
    fn = SimpleNamespace(name=name, arguments=raw if raw is not None else json.dumps(args))
    return SimpleNamespace(id=cid, type="function", function=fn)


def reply(*calls, content=None, reasoning=None):
    msg = SimpleNamespace(content=content, tool_calls=list(calls) or None, reasoning_content=reasoning)
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg)], usage=usage)


class FakeClient:
    def __init__(self, script):
        self.script = list(script)
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.requests.append(json.loads(json.dumps(kwargs, default=str)))
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


H2_SEARCH = {"origin": "Chennai", "destination": "Delhi", "date": "2026-08-22",
             "depart_before": "12:00", "max_price": 8000}


def policy(script, **kw):
    client = FakeClient(script)
    return OpenAICompatPolicy(model="fake", client=client, retry_base_s=0, **kw), client


def episode(p, h=2, lang="en", injector=None):
    g = gold(h)
    traj = run_episode(g["task_id"], h, TEMPLATE["requests"][lang], p, injector=injector, context=CONTEXT)
    return traj, verify(traj, g, traj.sold_out)


def test_scripted_model_solves_h2_and_prompt_has_session_date():
    p, client = policy([
        reply(call("search_flights", H2_SEARCH, "c1"), reasoning="need flights"),
        reply(call("book_flight", {"flight_id": "6E212"}, "c2")),
    ])
    traj, r = episode(p)
    assert r["success"] and r["num_steps_taken"] == 2
    assert "2026-08-21" in client.requests[0]["messages"][0]["content"]
    tool_msg = client.requests[1]["messages"][-1]
    assert tool_msg["role"] == "tool" and tool_msg["tool_call_id"] == "c1"
    assert "6E212" in tool_msg["content"]
    assert p.reasoning[0] == "need flights"
    assert p.usage == {"prompt_tokens": 20, "completion_tokens": 10, "model_calls": 2}


def test_localised_error_reaches_model_unescaped():
    p, client = policy([
        reply(call("search_flights", H2_SEARCH, "c1")),
        reply(call("search_flights", H2_SEARCH, "c2")),
        reply(call("book_flight", {"flight_id": "6E212"}, "c3")),
    ])
    inj = FailureInjector("transient", "zh", at_tool="search_flights")
    traj, r = episode(p, lang="zh", injector=inj)
    error_msg = client.requests[1]["messages"][-1]
    assert error_msg["tool_call_id"] == "c1"
    assert "\\u" not in error_msg["content"] and not error_msg["content"].isascii()
    assert r["recovered"] is True


def test_only_first_parallel_call_is_kept():
    p, client = policy([
        reply(call("search_flights", H2_SEARCH, "c1"), call("book_flight", {"flight_id": "AI440"}, "c1b")),
        reply(call("book_flight", {"flight_id": "6E212"}, "c2")),
    ])
    traj, r = episode(p)
    assistant = client.requests[1]["messages"][-2]
    assert [c["id"] for c in assistant["tool_calls"]] == ["c1"]
    assert r["booked_flight"] == "6E212"


def test_malformed_arguments_become_validation_error_and_episode_continues():
    p, client = policy([
        reply(call("search_flights", None, "c1", raw="{origin: Chennai")),
        reply(call("search_flights", H2_SEARCH, "c2")),
        reply(call("book_flight", {"flight_id": "6E212"}, "c3")),
    ])
    traj, r = episode(p)
    assert traj.steps[0]["error"]["error_type"] == "validation"
    assert r["first_error_step"] == 1 and r["success"]
    assert "JSON object" in client.requests[1]["messages"][-1]["content"]


def test_text_reply_ends_episode_unbooked():
    p, _ = policy([reply(content="Which airline do you prefer?")])
    traj, r = episode(p)
    assert traj.final_text == "Which airline do you prefer?"
    assert r["success"] is False and r["booked_flight"] is None


class Status(Exception):
    def __init__(self, code):
        super().__init__(f"status {code}")
        self.status_code = code


def test_client_errors_fail_fast_server_errors_retry():
    p, client = policy([Status(400)])
    with pytest.raises(InfraError):
        episode(p)
    assert len(client.requests) == 1

    p, client = policy([Status(503), Status(503), reply(call("search_flights", H2_SEARCH, "c1")),
                        reply(call("book_flight", {"flight_id": "6E212"}, "c2"))], max_retries=2)
    assert episode(p)[1]["success"]

    p, _ = policy([Status(503)] * 3, max_retries=2)
    with pytest.raises(InfraError):
        episode(p)


def test_step_limit_is_flagged():
    p, _ = policy([reply(call("resolve_city", {"name": "Chennai"}, f"c{i}")) for i in range(20)])
    traj, r = episode(p, h=4)
    assert traj.hit_step_limit and not r["success"]
