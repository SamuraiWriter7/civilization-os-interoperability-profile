from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from generate_resolution_receipt import (
    ROOT,
    build_resolved_links,
    build_resolved_stages,
    load_yaml,
    resolve_repository_path,
    sha256_digest,
)


SCHEMA_PATH = (
    ROOT
    / "schemas"
    / "interoperability-resolution-receipt.schema.json"
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(
            f"{path.relative_to(ROOT)} must contain a JSON object."
        )

    return data


def format_json_path(error: Any) -> str:
    if not error.absolute_path:
        return "<root>"

    parts: list[str] = []

    for part in error.absolute_path:
        if isinstance(part, int):
            parts.append(f"[{part}]")
        else:
            if parts:
                parts.append(".")
            parts.append(str(part))

    return "".join(parts)


def schema_errors(
    instance: dict[str, Any],
    schema: dict[str, Any],
) -> list[str]:
    validator = Draft202012Validator(
        schema,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )

    errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: tuple(
            str(part)
            for part in error.absolute_path
        ),
    )

    return [
        f"{format_json_path(error)}: {error.message}"
        for error in errors
    ]


def verify_locked_file(
    label: str,
    reference: str,
    expected_digest: str,
) -> list[str]:
    errors: list[str] = []

    try:
        path = resolve_repository_path(
            reference
        )
    except Exception as exc:
        return [
            f"{label}: {exc}"
        ]

    actual_digest = sha256_digest(path)

    if actual_digest != expected_digest:
        errors.append(
            f"{label} digest mismatch: "
            f"expected {expected_digest}, "
            f"received {actual_digest}."
        )

    return errors


def semantic_errors(
    receipt: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    profile_lock = receipt.get(
        "profile",
        {},
    )

    if not isinstance(profile_lock, dict):
        return [
            "profile must be an object."
        ]

    profile_ref = str(
        profile_lock.get(
            "profile_ref",
            "",
        )
    )

    errors.extend(
        verify_locked_file(
            "profile",
            profile_ref,
            str(
                profile_lock.get(
                    "digest",
                    "",
                )
            ),
        )
    )

    try:
        profile_path = resolve_repository_path(
            profile_ref
        )

        profile = load_yaml(
            profile_path
        )

    except Exception as exc:
        return errors + [
            f"Unable to load locked profile: {exc}"
        ]

    if (
        profile_lock.get("profile_id")
        != profile.get("profile_id")
    ):
        errors.append(
            "Receipt profile_id does not match "
            "the referenced profile."
        )

    if (
        profile_lock.get("schema_version")
        != profile.get("schema_version")
    ):
        errors.append(
            "Receipt profile schema_version does not "
            "match the referenced profile."
        )

    registry_fields = {
        "identifier": "identifier_registry",
        "compatibility": "compatibility_registry",
        "adapter": "adapter_registry",
    }

    loaded_registries: dict[
        str,
        dict[str, Any],
    ] = {}

    receipt_registries = receipt.get(
        "registries",
        {},
    )

    if not isinstance(
        receipt_registries,
        dict,
    ):
        return errors + [
            "registries must be an object."
        ]

    for receipt_name, profile_name in (
        registry_fields.items()
    ):
        lock = receipt_registries.get(
            receipt_name,
            {},
        )

        binding = profile.get(
            profile_name,
            {},
        )

        if not isinstance(lock, dict):
            errors.append(
                f"Registry lock '{receipt_name}' "
                "must be an object."
            )
            continue

        if not isinstance(binding, dict):
            errors.append(
                f"Profile binding '{profile_name}' "
                "must be an object."
            )
            continue

        registry_ref = str(
            lock.get(
                "registry_ref",
                "",
            )
        )

        errors.extend(
            verify_locked_file(
                f"{receipt_name} registry",
                registry_ref,
                str(
                    lock.get(
                        "digest",
                        "",
                    )
                ),
            )
        )

        if (
            lock.get("registry_id")
            != binding.get("registry_id")
        ):
            errors.append(
                f"{receipt_name} registry_id does not "
                "match the profile binding."
            )

        if (
            lock.get("version")
            != binding.get("version")
        ):
            errors.append(
                f"{receipt_name} registry version does "
                "not match the profile binding."
            )

        if (
            registry_ref
            != binding.get("registry_ref")
        ):
            errors.append(
                f"{receipt_name} registry_ref does not "
                "match the profile binding."
            )

        try:
            registry_path = (
                resolve_repository_path(
                    registry_ref
                )
            )

            registry = load_yaml(
                registry_path
            )

            loaded_registries[
                receipt_name
            ] = registry

            if (
                lock.get("registry_id")
                != registry.get("registry_id")
            ):
                errors.append(
                    f"{receipt_name} registry_id does "
                    "not match the registry document."
                )

            if (
                lock.get("version")
                != registry.get("version")
            ):
                errors.append(
                    f"{receipt_name} registry version "
                    "does not match the registry document."
                )

        except Exception as exc:
            errors.append(
                f"Unable to load {receipt_name} "
                f"registry: {exc}"
            )

    expected_stages = build_resolved_stages(
        profile
    )

    if (
        receipt.get("resolved_stages")
        != expected_stages
    ):
        errors.append(
            "resolved_stages does not match the "
            "current profile stage snapshot."
        )

    compatibility_registry = (
        loaded_registries.get(
            "compatibility"
        )
    )

    if compatibility_registry is not None:
        try:
            expected_links = (
                build_resolved_links(
                    profile,
                    compatibility_registry,
                )
            )

            if (
                receipt.get("resolved_links")
                != expected_links
            ):
                errors.append(
                    "resolved_links does not match "
                    "the current compatibility resolution."
                )

        except Exception as exc:
            errors.append(
                f"Unable to resolve compatibility "
                f"links: {exc}"
            )

    resolution_policy = profile.get(
        "resolution_policy",
        {},
    )

    if not isinstance(
        resolution_policy,
        dict,
    ):
        errors.append(
            "Profile resolution_policy must "
            "be an object."
        )
    else:
        required_true_fields = (
            "require_resolution_receipt",
            "require_digest_lock",
            "require_exact_stage_snapshot",
            "require_conformance_handoff",
        )

        for field in required_true_fields:
            if (
                resolution_policy.get(field)
                is not True
            ):
                errors.append(
                    f"resolution_policy.{field} "
                    "must be true."
                )

        if (
            resolution_policy.get(
                "handoff_target"
            )
            != "kazene-protocol-conformance-suite"
        ):
            errors.append(
                "resolution_policy.handoff_target "
                "must be "
                "'kazene-protocol-conformance-suite'."
            )

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a Civilization OS "
            "interoperability resolution receipt."
        )
    )

    parser.add_argument(
        "receipt",
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    receipt_path = args.receipt.resolve()

    print(
        "=== Interoperability Resolution "
        "Receipt Validation ==="
    )

    try:
        schema = load_json(
            SCHEMA_PATH
        )

        Draft202012Validator.check_schema(
            schema
        )

        receipt = load_yaml(
            receipt_path
        )

    except Exception as exc:
        print(f"[fatal] {exc}")
        return 1

    print(
        f"[validate-receipt] "
        f"{receipt_path.relative_to(ROOT)}"
    )

    errors = schema_errors(
        receipt,
        schema,
    )

    if errors:
        for error in errors:
            print(
                f"[schema-error] {error}"
            )

        return 1

    print("[schema-ok]")

    errors = semantic_errors(
        receipt
    )

    if errors:
        for error in errors:
            print(
                f"[semantic-error] {error}"
            )

        return 1

    print("[semantic-ok]")
    print("[digest-lock-ok]")
    print(
        "[conformance-handoff-ready] "
        "kazene-protocol-conformance-suite"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
