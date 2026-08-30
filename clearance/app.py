"""CLEARANCE gateway + console API (spec sections 4, 9, 12).

Drop-in OpenAI-compatible: point any client at http://localhost:8000/v1 and it
gets a completion, a governed action, and an immutable ledger row. Text streams
immediately (never held); only side effects wait at the latch.
"""
from __future__ import annotations

import time
import json
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import get_config
from .schemas import ChatCompletionRequest
from .policy import engine, loader, gate
from .latch import LATCH
from . import ledger, feedback, metrics, replay
from .detectors.embeddings import backend_name as emb_backend
from .detectors.nlp import nlp_backend

app = FastAPI(title="CLEARANCE", version="0.1.0",
              description="The decision layer above detection. Gate the action, not the answer.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])

ledger.init()
feedback.init()


# --- verdict -> content transform (text is never HELD, only annotated/redacted)
def _apply_to_content(content: str, decision) -> str:
    v = decision.verdict
    rv = decision.risk
    if v == "annotate":
        note = "\n\n⚠️ CLEARANCE: unverified against source — " + (
            "; ".join(rv.unsupported_claims[:1]) or decision.rationale[:120])
        return content + note
    if v == "redact":
        out = content
        for h in rv.pii_entities:
            if not h.in_context:
                out = out.replace(h.text, "█" * max(4, len(h.text)))
        for claim in rv.unsupported_claims:
            out = out.replace(claim, "[redacted: unverified claim]")
        return out
    return content


def _gateway_decide(body: ChatCompletionRequest):
    cfg = get_config()
    ext = body.clearance or {}
    policy_name = ext.get("policy") or cfg.default_policy
    context = ext.get("retrieved") or []
    conversation_id = ext.get("conversation_id") or "single"
    turn_index = int(ext.get("turn_index") or 0)

    messages = [m.model_dump() for m in body.messages]
    user_turn = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_turn = m.get("content") or ""
            break

    # upstream model call (fixture cache -> live -> recorded stub)
    from .llm import complete, content_of
    t0 = time.perf_counter()
    completion = complete(messages, model=body.model, temperature=body.temperature)
    upstream_ms = round((time.perf_counter() - t0) * 1000, 2)
    response_text = content_of(completion)

    # action can come from the clearance extension or from returned tool_calls
    action_tool = (ext.get("action") or {}).get("tool")
    action_args = (ext.get("action") or {}).get("arguments", {})
    msg0 = completion.get("choices", [{}])[0].get("message", {})
    if not action_tool and msg0.get("tool_calls"):
        tc = msg0["tool_calls"][0]
        action_tool = tc.get("function", {}).get("name")

    decision = engine.evaluate(
        response=response_text, context=context, user_turn=user_turn,
        action_tool=action_tool, action_args=action_args, policy_name=policy_name,
        conversation_id=conversation_id, turn_index=turn_index,
        request_id=f"req-{uuid.uuid4().hex[:10]}",
    )

    pack, _ = loader.load(policy_name)
    latch_result = LATCH.resolve(decision, pack, timed_out=False)
    ledger.append(decision)
    if decision.escalate:
        feedback.enqueue(decision.request_id, decision.use_case, response_text,
                         decision.rationale, decision.verdict,
                         {"fused": decision.risk.fused,
                          "categories": list(decision.risk.categories)})
    decision.latency_ms["upstream"] = upstream_ms
    return decision, latch_result, response_text, completion


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = ChatCompletionRequest(**(await request.json()))
    decision, latch_result, response_text, completion = _gateway_decide(body)
    governed = _apply_to_content(response_text, decision)
    clearance_meta = {
        "verdict": decision.verdict, "band": decision.band,
        "tier_reached": decision.tier_reached, "escalate": decision.escalate,
        "action": decision.action.model_dump() if decision.action else None,
        "action_released": latch_result["action_released"],
        "latch_outcome": latch_result["outcome"],
        "policy_hash": decision.policy_hash[:16],
        "categories": sorted(decision.risk.categories),
        "ceg": decision.risk.ceg, "fused": decision.risk.fused,
        "accumulated_risk": decision.accumulated_risk,
        "rationale": decision.rationale, "request_id": decision.request_id,
        "latency_ms": decision.latency_ms,
    }

    now = int(time.time())
    message = {"role": "assistant", "content": governed}
    # only surface the tool_call if the latch released the action
    orig_tc = completion.get("choices", [{}])[0].get("message", {}).get("tool_calls")
    if orig_tc and latch_result["action_released"]:
        message["tool_calls"] = orig_tc

    payload = {
        "id": f"chatcmpl-{decision.request_id}", "object": "chat.completion",
        "created": now, "model": body.model or get_config().model,
        "choices": [{"index": 0, "message": message,
                     "finish_reason": "tool_calls" if message.get("tool_calls") else "stop"}],
        "usage": completion.get("usage", {}),
        "clearance": clearance_meta,
    }

    if body.stream:
        def sse():
            cid = payload["id"]
            head = {"id": cid, "object": "chat.completion.chunk", "created": now,
                    "model": payload["model"],
                    "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]}
            yield f"data: {json.dumps(head)}\n\n"
            # text streams immediately -- never held
            step = 24
            for i in range(0, len(governed), step):
                chunk = {"id": cid, "object": "chat.completion.chunk", "created": now,
                         "model": payload["model"],
                         "choices": [{"index": 0, "delta": {"content": governed[i:i+step]},
                                      "finish_reason": None}]}
                yield f"data: {json.dumps(chunk)}\n\n"
            tail = {"id": cid, "object": "chat.completion.chunk", "created": now,
                    "model": payload["model"], "clearance": clearance_meta,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
            yield f"data: {json.dumps(tail)}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(sse(), media_type="text/event-stream")

    return JSONResponse(payload)


# --- console API -------------------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True, "offline": get_config().offline,
            "embeddings_backend": emb_backend(), "nlp_backend": nlp_backend()}


@app.get("/api/policies")
def api_policies():
    out = []
    for name in loader.list_packs():
        pack, phash = loader.load(name)
        out.append({"name": name, "pack": pack.get("pack"),
                    "jurisdiction": pack.get("jurisdiction"),
                    "risk_appetite": pack.get("risk_appetite"),
                    "policy_hash": phash[:16],
                    "operating_point": pack.get("operating_point", {})})
    return {"policies": out}


@app.get("/api/policy/{name}")
def api_policy(name: str):
    pack, phash = loader.load(name)
    return {"name": name, "policy_hash": phash, "pack": pack}


@app.post("/api/tuning/recompute")
async def api_recompute(request: Request):
    body = await request.json()
    use_case = body.get("use_case", "support-assistant")
    overrides = body.get("overrides", {})
    t0 = time.perf_counter()
    result = metrics.recompute(use_case, overrides)
    result["recompute_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    return result


@app.get("/api/ledger")
def api_ledger(limit: int = 200, use_case: str | None = None, verdict: str | None = None):
    return {"rows": ledger.rows(limit, use_case, verdict)}


@app.get("/api/ledger/verify")
def api_ledger_verify():
    return ledger.verify_chain()


@app.post("/api/ledger/tamper")
async def api_ledger_tamper(request: Request):
    body = await request.json()
    ok = ledger.tamper(int(body.get("seq")), body.get("verdict", "allow"))
    return {"tampered": ok, "verify": ledger.verify_chain()}


@app.get("/api/replay/paired")
def api_replay_paired():
    out = replay.replay_paired()
    return {"pairs": [{k: v for k, v in p.items() if k != "decisions"} for p in out]}


@app.get("/api/replay/agentic")
def api_replay_agentic():
    r = replay.replay_agentic()
    return {"conversation_id": r.get("conversation_id"),
            "turns": [{k: v for k, v in t.items() if k != "decision"}
                      for t in r.get("turns", [])]}


@app.post("/api/seed")
def api_seed():
    decisions = replay.replay_all(write_ledger=True)
    return {"seeded": len(decisions), "verify": ledger.verify_chain()}


@app.get("/api/review/pending")
def api_review_pending():
    return {"queue": feedback.pending()}


@app.post("/api/review/resolve")
async def api_review_resolve(request: Request):
    body = await request.json()
    ok = feedback.resolve(int(body["id"]), bool(body["human_label"]),
                          body.get("reviewer", "risk-owner"))
    return {"resolved": ok}
