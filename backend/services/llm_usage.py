"""LLM API 사용량(토큰·추정 비용) 기록 — 실측용 공통 모듈.

왜: 앱별 월 API 비용이 지금은 추정치뿐이다. 호출마다 토큰을 한 줄씩 남겨
2~4주 실측으로 바꾼다. (형제앱에 같은 파일을 복사해 쓴다 — 패턴은 README 체크리스트.)

어디에 남나
- 항상: 로거 `llm_usage` 에 `[llm_usage] {json}` 한 줄 → Cloud Run 이면 Cloud Logging 에 남는다.
  집계: gcloud logging read 'textPayload:"[llm_usage]"' --format='value(textPayload)'
- 선택: env `LLM_USAGE_FILE` 이 있으면 그 경로(JSONL)에도 append — 로컬 개발용.
  Cloud Run 파일시스템은 재시작 때 사라지므로 운영 집계 근거로 쓰지 않는다.

원칙
- 기록 실패가 본 기능을 막지 않는다(예외 삼킴).
- 단가표에 없는 모델은 cost_usd=None — 0 으로 채우지 않는다(미확인은 null).
- 비용은 정가 기준 추정치다. 실제 청구는 콘솔이 원본.
- Claude 밖 호출(Gemini·OpenAI·fal·Voyage)은 log_units/log_gemini 로 같은 모양의 레코드를
  남긴다 — 토큰 또는 장수·초·건수만, 비용은 null.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any

logger = logging.getLogger("llm_usage")
# 앱 로깅 설정에 기대지 않는다 — 대부분의 앱이 루트 로거를 안 건드려 기본 수준(WARNING)에서
# info 가 통째로 버려진다(실측 2026-10-28: 원본 앱도 Cloud Logging 에 0줄이었다).
# 자기 출력(stdout)을 갖고 루트로 안 올려 보낸다 — 루트가 INFO 인 앱에서 두 줄이 되지 않게.
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

# $/1M tokens: (input, output, cache_write_5m, cache_read)
# 출처: https://platform.claude.com/docs/en/about-claude/pricing (확인 2026-10-27)
PRICES: dict[str, tuple[float, float, float, float]] = {
    "claude-fable-5-1":  (10.0, 50.0, 12.5, 0.25),
    "claude-mythos-5-1": (10.0, 50.0, 12.5, 0.25),
    "claude-fable-5":    (10.0, 50.0, 12.5, 1.0),
    "claude-mythos-5":   (10.0, 50.0, 12.5, 1.0),
    "claude-opus-5-5":   (4.0, 20.0, 5.0, 0.20),
    "claude-opus-5":     (5.0, 25.0, 6.25, 0.50),
    "claude-opus-4-8":   (5.0, 25.0, 6.25, 0.50),
    "claude-opus-4-7":   (5.0, 25.0, 6.25, 0.50),
    "claude-opus-4-6":   (5.0, 25.0, 6.25, 0.50),
    "claude-opus-4-5":   (5.0, 25.0, 6.25, 0.50),
    "claude-sonnet-5-5": (2.0, 10.0, 2.5, 0.10),
    "claude-sonnet-5":   (2.0, 10.0, 2.5, 0.20),
    "claude-sonnet-4-6": (3.0, 15.0, 3.75, 0.30),
    "claude-sonnet-4-5": (3.0, 15.0, 3.75, 0.30),
    "claude-haiku-5-5":  (0.10, 0.50, 0.125, 0.01),  # 프롬프트 100K 이하 기준
    "claude-haiku-4-5":  (1.0, 5.0, 1.25, 0.10),
}
# 'claude-sonnet-5' 가 'claude-sonnet-5-5' 를 먼저 먹지 않도록 긴 키부터 대조한다.
_KEYS_LONGEST_FIRST = sorted(PRICES, key=len, reverse=True)


def price_for(model: str) -> tuple[float, float, float, float] | None:
    """모델 ID(날짜 접미사 포함 가능)에 맞는 단가. 모르면 None."""
    m = (model or "").lower()
    for key in _KEYS_LONGEST_FIRST:
        if m == key or m.startswith(key + "-") or m.startswith(key + "@"):
            return PRICES[key]
    return None


def estimate_cost(model: str, usage: dict) -> float | None:
    p = price_for(model)
    if p is None:
        return None
    inp, out, cw, cr = p
    total = (
        usage.get("input_tokens", 0) * inp
        + usage.get("output_tokens", 0) * out
        + usage.get("cache_creation_input_tokens", 0) * cw
        + usage.get("cache_read_input_tokens", 0) * cr
    ) / 1_000_000
    return round(total, 6)


def build_record(app: str, model: str, usage: dict | None,
                 meta: dict[str, Any] | None = None) -> dict:
    u = usage or {}
    rec = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "app": app,
        "provider": "anthropic",
        "model": model,
        "input_tokens": int(u.get("input_tokens", 0) or 0),
        "output_tokens": int(u.get("output_tokens", 0) or 0),
        "cache_write_tokens": int(u.get("cache_creation_input_tokens", 0) or 0),
        "cache_read_tokens": int(u.get("cache_read_input_tokens", 0) or 0),
        "cost_usd": estimate_cost(model, u),
    }
    if meta:
        rec["meta"] = meta
    return rec


def usage_of(resp: Any) -> dict | None:
    """응답에서 usage dict 를 꺼낸다 — SDK 응답 객체(`.usage.model_dump()`)와 httpx JSON
    (`data["usage"]`) 둘 다. 꺼낼 수 없으면 None(예외 없음)."""
    try:
        if isinstance(resp, dict):
            u = resp.get("usage")
            return u if isinstance(u, dict) else None
        u = getattr(resp, "usage", None)
        if u is None:
            return None
        return u.model_dump() if hasattr(u, "model_dump") else dict(u)
    except Exception:  # noqa: BLE001
        return None


def log_reply(app: str, model: str, resp: Any,
              meta: dict[str, Any] | None = None) -> dict | None:
    """응답 객체를 그대로 받는 log_usage — stop_reason 은 응답에서 꺼내 meta 에 붙인다.
    SDK 를 쓰는 앱은 호출 지점마다 이 한 줄이면 된다. 실패해도 예외를 올리지 않는다."""
    try:
        if isinstance(resp, dict):
            stop = resp.get("stop_reason")
        else:
            stop = getattr(resp, "stop_reason", None)
        return log_usage(app, model, usage_of(resp), {**(meta or {}), "stop_reason": stop})
    except Exception:  # noqa: BLE001
        logger.debug("llm_usage 기록 실패", exc_info=True)
        return None


def _emit(rec: dict) -> None:
    line = json.dumps(rec, ensure_ascii=False)
    logger.info("[llm_usage] %s", line)
    path = os.environ.get("LLM_USAGE_FILE")
    if path:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def log_usage(app: str, model: str, usage: dict | None,
              meta: dict[str, Any] | None = None) -> dict | None:
    """호출 1건을 기록하고 레코드를 돌려준다. 실패해도 예외를 올리지 않는다."""
    try:
        rec = build_record(app, model, usage, meta)
        _emit(rec)
        return rec
    except Exception:  # noqa: BLE001 — 기록 실패가 본 기능을 막으면 안 된다
        logger.debug("llm_usage 기록 실패", exc_info=True)
        return None


# ── Claude 밖 호출 (Gemini·OpenAI·fal·Voyage) ─────────────────────────────────

def log_units(app: str, provider: str, model: str, *,
              input_tokens: int | None = None, output_tokens: int | None = None,
              units: dict[str, Any] | None = None,
              meta: dict[str, Any] | None = None) -> dict | None:
    """Claude 밖 호출 1건 — Claude 와 같은 레코드 모양으로 남긴다.

    토큰을 주는 응답이면 토큰을, 장수·초·건수로 과금되면 `units`(images·audio_seconds·texts…)
    에 담는다. 모르는 값은 None(0 아님). cost_usd 는 늘 None — 단가표(PRICES)는 Claude
    것뿐이고 남의 단가를 지어내지 않는다. 비용은 이 수량과 각 콘솔 청구서로 계산한다.
    """
    try:
        rec = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "app": app,
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_write_tokens": None,
            "cache_read_tokens": None,
            "cost_usd": None,
        }
        if units:
            rec["units"] = units
        if meta:
            rec["meta"] = meta
        _emit(rec)
        return rec
    except Exception:  # noqa: BLE001
        logger.debug("llm_usage 기록 실패", exc_info=True)
        return None


def log_gemini(app: str, model: str, resp: Any,
               meta: dict[str, Any] | None = None) -> dict | None:
    """google-genai 응답 1건. 토큰은 usage_metadata 에서, 만든 이미지 수는 inline_data
    파트를 세서 남긴다(이미지 모델은 장 단위 과금). 실패해도 예외를 올리지 않는다."""
    inp = out = None
    images = 0
    try:
        um = getattr(resp, "usage_metadata", None)
        if um is not None:
            inp = getattr(um, "prompt_token_count", None)
            out = getattr(um, "candidates_token_count", None)
        for cand in getattr(resp, "candidates", None) or []:
            for part in getattr(getattr(cand, "content", None), "parts", None) or []:
                if getattr(part, "inline_data", None) is not None:
                    images += 1
    except Exception:  # noqa: BLE001
        pass
    return log_units(app, "google", model, input_tokens=inp, output_tokens=out,
                     units={"images": images} if images else None, meta=meta)
