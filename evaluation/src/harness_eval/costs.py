"""Token → US-dollar cost estimation for the SDLC harness.

Cost is estimated from per-model input/output prices and the token counts a
trial consumed. The pipeline is OpenAI-compatible (ChatOpenAI / ChatNVIDIA
behind a common facade), so most runs route through a known model name; when
a model is not in the table, we fall back to a configurable default so a cost
number is always produced (plus a flag so callers can surface "using fallback").

Prices are per **1M tokens**. Rates are a best-effort snapshot of public
list prices; they are meant for *relative* cost comparison between runs, not
as a billing invoice. Edit ``PRICES`` for your deployment's negotiated rates.
"""

from __future__ import annotations

from typing import Any

# price in USD per 1M tokens, keyed by a case-insensitive substring of the
# model name. Match order matters: check the most specific model names first.
PRICES: dict[str, dict[str, float]] = {
    # ── Ollama Cloud models (upstream vendor list prices) ─────────────────
    # IMPORTANT: Ollama Cloud itself is NOT billed per token. It is a
    # subscription (Free/Pro/Max/Team) metered by per-model "usage level"
    # 1-4, and it publishes no per-token rate. These entries are therefore a
    # PROXY: what this workload would cost on the model's own vendor API.
    # They make cost_usd comparable across models and runs — they are not
    # your Ollama bill. Verified 2026-08-27; re-check before quoting.
    #
    # These must precede the generic "qwen3" / "minimax" keys further down,
    # which would otherwise shadow them under substring matching.
    #
    # DeepSeek moved to peak/off-peak rates at 16:00 UTC on 2026-08-16.
    # Peak (UTC 01:00-04:00 and 06:00-10:00) is exactly 2x the values below;
    # off-peak covers the other 17h/day and is used here as the base rate.
    # Cache-HIT input is $0.007/M — 31x cheaper than the cache-miss rate
    # below — which is why cached_tokens is now captured (see usage_capture).
    "deepseek-v4-flash": {"input": 0.22, "output": 0.66},
    # GLM (Z.ai / Zhipu)
    "glm-5.3-flash": {"input": 0.15, "output": 0.50},
    "glm-5.2": {"input": 1.40, "output": 4.40},          # cached input $0.26
    # Moonshot Kimi
    "kimi-k3": {"input": 3.00, "output": 15.00},         # cache-hit $0.30
    "kimi-k2.7-code": {"input": 0.95, "output": 4.00},   # cache-hit $0.19
    "kimi-k2.6": {"input": 0.95, "output": 4.00},
    # MiniMax (m3 promo rate, <=512K input; 2x above that)
    "minimax-m3": {"input": 0.30, "output": 1.20},
    "minimax-m2.7": {"input": 0.24, "output": 0.96},     # cache read $0.06
    # Alibaba Qwen (International/Singapore endpoint; CN endpoint is cheaper)
    "qwen3.5-flash": {"input": 0.10, "output": 0.40},
    "qwen3.5-plus": {"input": 0.40, "output": 2.40},
    "qwen3.5": {"input": 0.60, "output": 3.60},
    # Others
    "mistral-large-3": {"input": 0.50, "output": 1.50},
    "gpt-oss": {"input": 0.09, "output": 0.45},          # OpenAI list rate
    #
    # NOT YET PRICED — no rate found on 2026-08-27, so these still fall back:
    #   glm-5.1, deepseek-v4-pro (output $1.98 off-peak known, input not
    #   published post-2026-08-16), nemotron-3-{ultra,super,nano}, gemma4.
    # Add them here rather than letting DEFAULT_PRICE invent a number.

    # Anthropic Claude 3.7 Sonnet
    "claude-3-7-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
    "claude-3-opus": {"input": 15.00, "output": 75.00},
    # OpenAI GPT-4o / 4.1 family. More-specific model names must precede their
    # shorter parent so substring matching picks the right rate.
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "gpt-4.1": {"input": 2.00, "output": 8.00},
    # OpenAI o-series (reasoning)
    "o3": {"input": 2.00, "output": 8.00},
    "o4-mini": {"input": 1.10, "output": 4.40},
    # OpenAI GPT-4 Turbo / gpt-4 (legacy)
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    # OpenAI GPT-3.5 (legacy)
    "gpt-3.5": {"input": 0.50, "output": 1.50},
    # Mistral / Mixtral
    "mistral-large": {"input": 2.00, "output": 6.00},
    "mistral-medium": {"input": 2.70, "output": 8.10},
    "mistral-small": {"input": 1.00, "output": 3.00},
    "mixtral": {"input": 0.60, "output": 2.40},
    # Llama 3.1 (Together AI / Fireworks list rates as representative)
    "llama-3.1-405b": {"input": 3.50, "output": 3.50},
    "llama-3.1-70b": {"input": 0.88, "output": 0.88},
    "llama-3.1-8b": {"input": 0.18, "output": 0.18},
    "llama-3.3-70b": {"input": 0.88, "output": 0.88},
    # Qwen
    "qwen3": {"input": 0.60, "output": 2.40},
    "qwen2.5": {"input": 0.60, "output": 2.40},
    "minimax": {"input": 0.30, "output": 1.10},
}

# ── Add your deployment's endpoint here ──────────────────────────────────
# The model name now reaches this table (the usage handler records it from
# response_metadata; before that fix `model` was always None and EVERY run
# silently used DEFAULT_PRICE below, so the PRICES table above was dead code
# on the pipeline path).
#
# A run priced by the fallback produces dollar figures that are arbitrary —
# they compare runs against each other, but they are NOT the real spend, and
# any budget expressed in dollars (e.g. the $1.00 cap) is meaningless against
# them. Check `used_fallback_price` in the grader output before quoting a
# cost. Add the real rate here to make the numbers real, e.g.:
#
#     "deepseek-v4-flash": {"input": <$/1M in>, "output": <$/1M out>},

# Fallback when no model name matches — this keeps a cost estimate flowing for
# arbitrary / self-hosted OpenAI-compatible endpoints.
DEFAULT_PRICE: dict[str, float] = {"input": 1.00, "output": 3.00}


def get_prices(model: str | None) -> tuple[dict[str, float], bool]:
    """Return ``(prices, used_fallback)`` for a model name.

    ``prices`` is the input/output per-1M-token rate in USD. ``used_fallback``
    is True when the model was not matched and ``DEFAULT_PRICE`` was used.
    """
    if model:
        norm = model.lower()
        for key, prices in PRICES.items():
            if key in norm:
                return prices, False
    return dict(DEFAULT_PRICE), True


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str | None = None,
    prices: dict[str, float] | None = None,
    used_fallback: bool | None = None,
) -> dict[str, Any]:
    """Estimate the USD cost of a token usage.

    Args:
        input_tokens: number of prompt/input tokens consumed.
        output_tokens: number of completion/output tokens consumed.
        model: model name, used to look up prices. Falls back when unknown.
        prices: optional override ``{"input": $/1M, "output": $/1M}``.
        used_fallback: state explicitly whether ``prices`` came from the
            fallback. Callers that resolve prices themselves via
            :func:`get_prices` MUST forward the flag it returned — passing
            resolved prices in used to reset the flag to False, which
            stamped "trustworthy price" on every fallback-priced run.

    Returns:
        A dict:
          - ``input_tokens`` / ``output_tokens`` (echoed)
          - ``cost_usd``: the computed cost
          - ``input_price`` / ``output_price``: the $ per 1M used
          - ``used_fallback_price``: True if the default price was used
    """
    if prices:
        p = prices
        resolved_fallback = False
    else:
        p, resolved_fallback = get_prices(model)
    # An explicit flag always wins over the inference above.
    if used_fallback is not None:
        resolved_fallback = used_fallback
    cost = (input_tokens or 0) * p["input"] / 1_000_000 + (
        output_tokens or 0
    ) * p["output"] / 1_000_000
    return {
        "input_tokens": int(input_tokens or 0),
        "output_tokens": int(output_tokens or 0),
        "cost_usd": round(cost, 6),
        "input_price": p["input"],
        "output_price": p["output"],
        "used_fallback_price": bool(resolved_fallback),
    }
