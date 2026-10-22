"""Profiles (fleet amendment sections 6.1 and 12.A).

A profile is one way to run one CLI on one model: adapter, command template,
model, priority, concurrency, declared family, role eligibility and optional
gateway routing.

The operator's saved entries in ``prompts.json`` are really profiles â€” the
same prefix repeated per project.  :func:`import_prompts` turns that file
into profiles and drops the obsolete prompt text (fleet amendment Â§12.A).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from pmk.plat import read_text

#: Model strings that look like aliases rather than concrete models.  A
#: profile built from one is marked ``family = "unknown"`` (fleet Â§12.A).
#:
#: The test is deliberately narrow: ``--model free`` is a router alias, but
#: ``deepseek-v4-flash-free`` is a concrete model in a known family.  Only
#: the whole string being an alias, or the OpenRouter ``:free`` suffix,
#: counts.
ALIAS_PATTERNS = (
    re.compile(r"^free$", re.IGNORECASE),
    re.compile(r"^poor-", re.IGNORECASE),
    re.compile(r"^poorer?$", re.IGNORECASE),
    re.compile(r":free$", re.IGNORECASE),
    re.compile(r"^auto$", re.IGNORECASE),
)

#: Known family hints.  A family is **declared**, never verified
#: (fleet amendment D-L11, D-L12).
FAMILY_HINTS = {
    "deepseek": "deepseek",
    "claude": "anthropic",
    "anthropic": "anthropic",
    "gpt": "openai",
    "openai": "openai",
    "gemini": "google",
    "google": "google",
    "glm": "zhipu",
    "zai": "zhipu",
    "qwen": "alibaba",
    "llama": "meta",
    "mistral": "mistral",
    "grok": "xai",
    "nemotron": "nvidia",
    "muse": "minimax",
    "mimo": "xiaomi",
    "laguna": "poolside",
    "poolside": "poolside",
}


def guess_family(model: str) -> str:
    """Guess a declared family from a model string.

    Returns ``"unknown"`` when there is no confident match.  A profile with
    an unknown family can never serve as an independent verifier
    (fleet amendment D-L12).
    """
    text = (model or "").lower()
    for pattern in ALIAS_PATTERNS:
        if pattern.search(text):
            return "unknown"
    for needle, family in FAMILY_HINTS.items():
        if needle in text:
            return family
    return "unknown"


@dataclass
class Profile:
    """One profile."""

    id: str
    adapter: str = "generic"
    family: str = "unknown"
    priority: int = 100
    max_concurrent: int = 1
    via_gateway: bool = False
    roles: list = field(default_factory=list)
    argv_new: list = field(default_factory=list)
    argv_resume: list = field(default_factory=list)
    model: str = ""
    enabled: bool = True
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, obj: dict) -> "Profile":
        argv_new = [str(a) for a in (obj.get("argv_new") or [])]
        argv_resume = [str(a) for a in (obj.get("argv_resume") or [])]
        model = str(obj.get("model", ""))
        if not model:
            model = _model_from_argv(argv_new)
        return cls(
            id=str(obj.get("id", "")),
            adapter=str(obj.get("adapter", "generic")),
            family=str(obj.get("family") or "unknown"),
            priority=int(obj.get("priority", 100)),
            max_concurrent=int(obj.get("max_concurrent", 1)),
            via_gateway=bool(obj.get("via_gateway", False)),
            roles=[str(r) for r in (obj.get("roles") or [])],
            argv_new=argv_new,
            argv_resume=argv_resume,
            model=model,
            enabled=bool(obj.get("enabled", True)),
            raw=dict(obj),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "adapter": self.adapter,
            "family": self.family,
            "priority": self.priority,
            "max_concurrent": self.max_concurrent,
            "via_gateway": self.via_gateway,
            "roles": self.roles,
            "argv_new": self.argv_new,
            "argv_resume": self.argv_resume,
            "model": self.model,
            "enabled": self.enabled,
        }

    def eligible_for(self, task_type: str) -> bool:
        """Can this profile take a task of *task_type*?

        A profile with no ``roles`` list is eligible for everything, which
        keeps hand-written profiles usable without ceremony.
        """
        if not self.roles:
            return True
        return task_type in self.roles

    def supports_resume(self) -> bool:
        return bool(self.argv_resume)


def _model_from_argv(argv: list[str]) -> str:
    """Extract a model string from an argv template."""
    for index, token in enumerate(argv):
        if token == "--model" and index + 1 < len(argv):
            return argv[index + 1]
        if token.startswith("--model="):
            return token.split("=", 1)[1]
    return ""


def load_profiles(repo) -> list[Profile]:
    """Load profiles from ``agents.toml``."""
    from pmk.policy import load_agents
    agents = load_agents(repo)
    return [Profile.from_dict(p) for p in agents["profiles"] if p.get("id")]


def profile_index(profiles: list[Profile]) -> dict[str, Profile]:
    return {p.id: p for p in profiles}


# ---------------------------------------------------------------------------
# Importing the operator's prompts.json
# ---------------------------------------------------------------------------

def _split_prefix(prefix: str) -> tuple[str, str]:
    """Split a prefix into ``(tool, model)``."""
    tokens = prefix.split()
    tool = tokens[0] if tokens else ""
    model = ""
    for index, token in enumerate(tokens):
        if token == "--model" and index + 1 < len(tokens):
            model = tokens[index + 1]
            break
        if token.startswith("--model="):
            model = token.split("=", 1)[1]
            break
    return tool, model


def _argv_from_entry(entry: dict) -> list[str]:
    """Build an argv template from a legacy launcher entry.

    The legacy entry is ``<prefix> "<prompt>" <suffix>``.  The prompt becomes
    the ``{prompt}`` placeholder; the working directory becomes ``{cwd}``.
    """
    prefix = str(entry.get("prefix", "")).strip()
    suffix = str(entry.get("suffix", "")).strip()
    tool, model = _split_prefix(prefix)
    argv: list[str] = [tool] if tool else []
    for token in prefix.split()[1:]:
        if token == "--model":
            argv.append(token)
        elif token.startswith("--model="):
            argv.append(token)
        elif model and token == model:
            continue
        else:
            argv.append(token)
    argv.append("{prompt}")
    for token in suffix.split():
        if token in ("--in", "--dir"):
            argv.append(token)
            argv.append("{cwd}")
        else:
            argv.append(token)
    return argv


def import_prompts(path: str | Path, *, existing: list[Profile] | None = None,
                   prefix: str = "imported") -> list[Profile]:
    """Generate profiles from the operator's ``prompts.json``.

    One profile per distinct prefix/suffix pair.  Profiles that differ only
    in their project folder collapse into one, because the folder is a
    launch-time value, not a property of the tool.

    The saved prompt text is **dropped**: the Fleet sends its own work
    order, and the legacy prompt told the agent to run the old pull-based
    protocol (``wf/wf.py claim``), which the fleet amendment D-L2 replaces.
    """
    target = Path(path)
    try:
        raw = json.loads(read_text(target))
    except (OSError, ValueError) as exc:
        raise ValueError(f"cannot read {target}: {exc}") from exc

    if isinstance(raw, list):
        raw = {"prompts": raw}
    entries = raw.get("prompts") or []

    known = {(p.raw.get("prefix"), p.raw.get("suffix")) for p in (existing or [])}
    profiles: list[Profile] = []
    seen: set[tuple] = set()

    for entry in entries:
        prefix_text = str(entry.get("prefix", "")).strip()
        suffix_text = str(entry.get("suffix", "")).strip()
        cwd_text = str(entry.get("cwd", "")).strip()
        if not prefix_text:
            continue
        # The project folder is a launch-time value, not a property of the
        # tool, so the dedup key replaces it with a placeholder.  Two
        # entries that differ only in their folder collapse into one
        # profile (fleet amendment section 12.A).
        key = (prefix_text, suffix_text.replace(cwd_text, "{cwd}") if cwd_text
               else suffix_text)
        if key in seen or key in known:
            continue
        seen.add(key)

        tool, model = _split_prefix(prefix_text)
        argv = _argv_from_entry(entry)
        profile_id = _profile_id(tool, model, prefix)
        profiles.append(Profile(
            id=profile_id,
            adapter=tool or "generic",
            family=guess_family(model),
            priority=_priority_for(tool),
            max_concurrent=_concurrency_for(tool),
            via_gateway=False,
            roles=["implement", "review"],
            argv_new=argv,
            argv_resume=[],
            model=model,
            raw={"prefix": prefix_text, "suffix": suffix_text,
                 "source": str(target)},
        ))
    return profiles


def _profile_id(tool: str, model: str, prefix: str) -> str:
    """A stable, readable id for an imported profile."""
    base = tool or "profile"
    slug = re.sub(r"[^a-z0-9]+", "-", (model or prefix).lower()).strip("-")
    slug = slug[:40].strip("-")
    return f"{base}-{slug}" if slug else base


def _priority_for(tool: str) -> int:
    """Initial priority (fleet amendment guess G-F3).

    Hermes first, because the operator reports its free models are not
    rate limited.  Cline last, because its models have per-model daily
    limits.
    """
    return {"hermes": 10, "kilo": 20, "pi": 30, "cline": 40,
            "opencode": 5}.get(tool.lower(), 50)


def _concurrency_for(tool: str) -> int:
    return {"hermes": 4, "kilo": 3, "pi": 2, "cline": 1,
            "opencode": 2}.get(tool.lower(), 1)


def render_agents_toml(profiles: list[Profile]) -> str:
    """Render profiles as an ``agents.toml`` document."""
    lines = [
        "# agents.toml â€” Fleet profiles.",
        "#",
        "# Generated by `pmk fleet import-prompts`.  Hand-editing is allowed;",
        "# the profile *schema* is a class K change (fleet amendment section 11).",
        "",
    ]
    for profile in profiles:
        lines.append("[[profile]]")
        lines.append(f'id = "{profile.id}"')
        lines.append(f'adapter = "{profile.adapter}"')
        lines.append(f'family = "{profile.family}"')
        lines.append(f"priority = {profile.priority}")
        lines.append(f"max_concurrent = {profile.max_concurrent}")
        lines.append(f"via_gateway = {'true' if profile.via_gateway else 'false'}")
        roles = ", ".join(f'"{r}"' for r in profile.roles)
        lines.append(f"roles = [{roles}]")
        lines.append(f"argv_new = {_toml_list(profile.argv_new)}")
        lines.append(f"argv_resume = {_toml_list(profile.argv_resume)}")
        lines.append("")
    return "\n".join(lines)


def _toml_list(values: list[str]) -> str:
    return "[" + ", ".join(f'"{v}"' for v in values) + "]"
