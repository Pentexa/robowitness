"""Policy profile catalog: builtin presets + user-saved profiles (SQLite)."""

import uuid
from datetime import datetime, timezone

from app.db import get_db
from app.schemas.policy import PolicyConfig
from app.schemas.policy_profile import PolicyProfile, PolicyProfileCreate

_SEED_TS = "2026-01-01T00:00:00+00:00"


def _profile(pid: str, name: str, desc: str, policy: dict, source: str, ts: str) -> PolicyProfile:
    return PolicyProfile(
        profile_id=pid,
        name=name,
        description=desc,
        policy=PolicyConfig(**policy),
        source=source,  # type: ignore[arg-type]
        created_at=ts,
        updated_at=ts,
    )


def builtin_profiles() -> list[PolicyProfile]:
    return [
        _profile(
            "profile-baseline",
            "Eski ayarlar (baseline)",
            "Robotun fabrika/başlangıç ayarları; karşılaştırma için sabit referans.",
            dict(
                id="baseline-v1",
                max_speed_mps=0.75,
                safe_distance_m=0.30,
                reaction_margin_m=0.05,
                brake_gain=1.5,
                obstacle_prediction_horizon_s=0.0,
            ),
            "builtin",
            _SEED_TS,
        ),
        _profile(
            "profile-balanced",
            "Dengeli",
            "Orta hız, geniş güvenli mesafe ve engel tahmini açık.",
            dict(
                id="candidate-balanced",
                max_speed_mps=0.45,
                safe_distance_m=0.85,
                reaction_margin_m=0.15,
                brake_gain=3.0,
                obstacle_prediction_horizon_s=0.6,
            ),
            "builtin",
            _SEED_TS,
        ),
        _profile(
            "profile-cautious",
            "Temkinli",
            "Yavaş ve uzaktan kaçınan ayar; süre aşımı riski taşır.",
            dict(
                id="candidate-cautious",
                max_speed_mps=0.30,
                safe_distance_m=1.20,
                reaction_margin_m=0.30,
                brake_gain=4.0,
                obstacle_prediction_horizon_s=1.0,
            ),
            "builtin",
            _SEED_TS,
        ),
        _profile(
            "profile-fast",
            "Hızlı",
            "Yüksek hız, dar mesafe; hızlı ama yakın geçiş/çarpışma riski yüksek.",
            dict(
                id="candidate-fast",
                max_speed_mps=0.95,
                safe_distance_m=0.40,
                reaction_margin_m=0.05,
                brake_gain=1.5,
                obstacle_prediction_horizon_s=0.3,
            ),
            "builtin",
            _SEED_TS,
        ),
    ]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_user_profiles(workspace: str = "default") -> list[PolicyProfile]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT profile_json FROM policy_profiles WHERE workspace_id = ? "
            "ORDER BY created_at ASC",
            (workspace,),
        ).fetchall()
    return [PolicyProfile.model_validate_json(r["profile_json"]) for r in rows]


def list_profiles(workspace: str = "default") -> list[PolicyProfile]:
    return builtin_profiles() + list_user_profiles(workspace)


def get_profile(profile_id: str, workspace: str = "default") -> PolicyProfile | None:
    for p in list_profiles(workspace):
        if p.profile_id == profile_id:
            return p
    return None


def find_duplicate(
    name: str, exclude_id: str | None = None, workspace: str = "default"
) -> PolicyProfile | None:
    wanted = name.strip().lower()
    for p in list_profiles(workspace):
        if exclude_id is not None and p.profile_id == exclude_id:
            continue
        if p.name.strip().lower() == wanted:
            return p
    return None


def create_profile(data: PolicyProfileCreate, workspace: str = "default") -> PolicyProfile:
    now = _now()
    profile = PolicyProfile(
        **data.model_dump(),
        profile_id=f"profile-{uuid.uuid4().hex[:12]}",
        source="user",
        created_at=now,
        updated_at=now,
    )
    with get_db() as conn:
        conn.execute(
            "INSERT INTO policy_profiles (profile_id, profile_json, created_at, updated_at, "
            "workspace_id) VALUES (?, ?, ?, ?, ?)",
            (profile.profile_id, profile.model_dump_json(), now, now, workspace),
        )
        conn.commit()
    return profile


def update_profile(
    profile_id: str, data: PolicyProfileCreate, workspace: str = "default"
) -> PolicyProfile | None:
    existing = get_profile(profile_id, workspace)
    if existing is None or existing.source != "user":
        return None
    profile = PolicyProfile(
        **data.model_dump(),
        profile_id=profile_id,
        source="user",
        created_at=existing.created_at,
        updated_at=_now(),
    )
    with get_db() as conn:
        conn.execute(
            "UPDATE policy_profiles SET profile_json = ?, updated_at = ? WHERE profile_id = ?",
            (profile.model_dump_json(), profile.updated_at, profile_id),
        )
        conn.commit()
    return profile


def delete_profile(profile_id: str, workspace: str = "default") -> bool:
    existing = get_profile(profile_id, workspace)
    if existing is None or existing.source != "user":
        return False
    with get_db() as conn:
        conn.execute("DELETE FROM policy_profiles WHERE profile_id = ?", (profile_id,))
        conn.commit()
    return True
