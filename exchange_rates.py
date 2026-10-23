"""Cached exchange-rate retrieval used by the public conversion strip."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data"
EXCHANGE_CACHE_FILE = DATA_DIR / "exchange_rate_cache.json"
EXCHANGE_CACHE_TTL_SECONDS = 60 * 60
EXCHANGE_SOURCE_NAME = "ExchangeRate-API Open Access"
EXCHANGE_SOURCE_URL = "https://www.exchangerate-api.com/docs/free"

def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def normalize_currency_code(value: Any, fallback: str) -> str:
    code = "".join(ch for ch in str(value or "").upper() if ch.isalpha())
    return code if len(code) == 3 else fallback

def normalize_currency_targets(value: Any, fallback: list[str] | None = None) -> list[str]:
    fallback = fallback or ["RUB"]
    if isinstance(value, list):
        raw = ",".join(str(item) for item in value)
    else:
        raw = str(value or "")
    targets: list[str] = []
    for chunk in raw.replace(";", ",").replace("|", ",").split(","):
        code = normalize_currency_code(chunk, "")
        if code and code not in targets:
            targets.append(code)
    return targets or fallback

def load_exchange_cache() -> dict[str, Any]:
    try:
        data = json.loads(EXCHANGE_CACHE_FILE.read_text("utf-8"))
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}

def save_exchange_cache(cache: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    EXCHANGE_CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), "utf-8")

def get_exchange_rate(base: str = "CNY", target: str = "RUB") -> dict[str, Any]:
    base_code = normalize_currency_code(base, "CNY")
    target_code = normalize_currency_code(target, "RUB")
    cache_key = f"{base_code}_{target_code}"
    cache = load_exchange_cache()
    cached = cache.get(cache_key) if isinstance(cache.get(cache_key), dict) else None
    now_ts = int(datetime.utcnow().timestamp())

    if cached and now_ts - int(cached.get("fetched_at_ts") or 0) < EXCHANGE_CACHE_TTL_SECONDS:
        return {**cached, "cached": True, "stale": False}

    if base_code == target_code:
        payload = {
            "base": base_code,
            "target": target_code,
            "pair": f"{base_code}/{target_code}",
            "rate": 1.0,
            "updated_at": utc_now_iso(),
            "fetched_at": utc_now_iso(),
            "fetched_at_ts": now_ts,
            "source": EXCHANGE_SOURCE_NAME,
            "source_url": EXCHANGE_SOURCE_URL,
        }
        cache[cache_key] = payload
        save_exchange_cache(cache)
        return {**payload, "cached": False, "stale": False}

    api_url = f"https://open.er-api.com/v6/latest/{base_code}"
    try:
        request = urllib.request.Request(
            api_url,
            headers={"User-Agent": "TLHDD-Auto-Export/1.0"},
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            remote = json.loads(response.read().decode("utf-8"))
        rates = remote.get("rates") if isinstance(remote, dict) else {}
        if not isinstance(rates, dict) or target_code not in rates:
            raise ValueError("汇率接口未返回目标币种")
        updated_ts = int(remote.get("time_last_update_unix") or now_ts)
        payload = {
            "base": base_code,
            "target": target_code,
            "pair": f"{base_code}/{target_code}",
            "rate": round(float(rates[target_code]), 4),
            "updated_at": datetime.utcfromtimestamp(updated_ts).replace(microsecond=0).isoformat() + "Z",
            "fetched_at": utc_now_iso(),
            "fetched_at_ts": now_ts,
            "source": str(remote.get("provider") or EXCHANGE_SOURCE_NAME),
            "source_url": EXCHANGE_SOURCE_URL,
        }
        cache[cache_key] = payload
        save_exchange_cache(cache)
        return {**payload, "cached": False, "stale": False}
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        if cached:
            return {**cached, "cached": True, "stale": True, "error": str(exc)}
        raise ValueError("暂时无法获取汇率") from exc

def get_exchange_rates(base: str = "CNY", targets: list[str] | None = None) -> dict[str, Any]:
    base_code = normalize_currency_code(base, "CNY")
    target_codes = normalize_currency_targets(targets or ["RUB"])
    cache = load_exchange_cache()
    now_ts = int(datetime.utcnow().timestamp())
    fetched_at = utc_now_iso()
    fresh: dict[str, dict[str, Any]] = {}
    stale: dict[str, dict[str, Any]] = {}
    need_fetch: list[str] = []

    for target in target_codes:
        cached = cache.get(f"{base_code}_{target}")
        if not isinstance(cached, dict):
            cached = None
        if target == base_code and cached is None:
            cached = {
                "base": base_code,
                "target": target,
                "pair": f"{base_code}/{target}",
                "rate": 1.0,
                "updated_at": fetched_at,
                "fetched_at": fetched_at,
                "fetched_at_ts": now_ts,
                "source": EXCHANGE_SOURCE_NAME,
                "source_url": EXCHANGE_SOURCE_URL,
            }
            cache[f"{base_code}_{target}"] = cached
        if cached and now_ts - int(cached.get("fetched_at_ts") or 0) < EXCHANGE_CACHE_TTL_SECONDS:
            fresh[target] = {**cached, "cached": True, "stale": False}
        elif cached:
            stale[target] = cached
            if target != base_code:
                need_fetch.append(target)
        elif target != base_code:
            need_fetch.append(target)

    remote_rates: dict[str, Any] = {}
    remote_error = ""
    if need_fetch:
        try:
            request = urllib.request.Request(
                f"https://open.er-api.com/v6/latest/{base_code}",
                headers={"User-Agent": "TLHDD-Auto-Export/1.0"},
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                remote = json.loads(response.read().decode("utf-8"))
            candidate_rates = remote.get("rates") if isinstance(remote, dict) else {}
            if not isinstance(candidate_rates, dict):
                raise ValueError("汇率接口未返回有效数据")
            remote_rates = candidate_rates
            updated_ts = int(remote.get("time_last_update_unix") or now_ts)
            updated_at = datetime.utcfromtimestamp(updated_ts).replace(microsecond=0).isoformat() + "Z"
            source = str(remote.get("provider") or EXCHANGE_SOURCE_NAME)
            for target in need_fetch:
                if target not in remote_rates:
                    continue
                cache[f"{base_code}_{target}"] = {
                    "base": base_code,
                    "target": target,
                    "pair": f"{base_code}/{target}",
                    "rate": round(float(remote_rates[target]), 4),
                    "updated_at": updated_at,
                    "fetched_at": fetched_at,
                    "fetched_at_ts": now_ts,
                    "source": source,
                    "source_url": EXCHANGE_SOURCE_URL,
                }
            save_exchange_cache(cache)
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError, TypeError, json.JSONDecodeError, OverflowError) as exc:
            remote_error = str(exc)

    rates: list[dict[str, Any]] = []
    for target in target_codes:
        if target in fresh:
            rates.append(fresh[target])
            continue
        cached = cache.get(f"{base_code}_{target}")
        if target == base_code:
            if not isinstance(cached, dict):
                cached = {"base": base_code, "target": target, "pair": f"{base_code}/{target}", "rate": 1.0}
            rates.append({**cached, "cached": target in stale, "stale": False})
            continue
        if isinstance(cached, dict) and cached.get("fetched_at_ts") == now_ts and target in remote_rates:
            rates.append({**cached, "cached": False, "stale": False})
        elif target in stale:
            rates.append({**stale[target], "cached": True, "stale": True, "error": remote_error or "汇率接口未返回目标币种"})
        else:
            raise ValueError("暂时无法获取汇率")

    is_stale = any(rate.get("stale") for rate in rates)
    updated_values = [str(rate.get("updated_at") or "") for rate in rates if rate.get("updated_at")]
    fetched_values = [str(rate.get("fetched_at") or "") for rate in rates if rate.get("fetched_at")]
    return {
        "base": base_code,
        "targets": target_codes,
        "rates": rates,
        "updated_at": min(updated_values) if updated_values else utc_now_iso(),
        "fetched_at": max(fetched_values) if fetched_values else utc_now_iso(),
        "source": rates[0].get("source", EXCHANGE_SOURCE_NAME) if rates else EXCHANGE_SOURCE_NAME,
        "source_url": rates[0].get("source_url", EXCHANGE_SOURCE_URL) if rates else EXCHANGE_SOURCE_URL,
        "cached": any(rate.get("cached") for rate in rates),
        "stale": is_stale,
    }

