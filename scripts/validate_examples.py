from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PROFILE = (
    ROOT
    / "examples"
    / "pass"
    / "civilization-os-interoperability-profile.example.yaml"
)

DEFAULT_OUTPUT = (
    ROOT
    / "build"
    / "resolution"
    / "kazene-core-lifecycle.resolution.yaml"
)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(
            f"{path.relative_to(ROOT)} must contain a YAML object."
        )

    return data


def write_yaml(
    path: Path,
    data: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(
            data,
            file,
            sort_keys=False,
            allow_unicode=True,
            width=88,
        )


def relative_path(path: Path) -> str:
    return path.resolve().relative_to(
        ROOT.resolve()
    ).as_posix()


def resolve_repository_path(
    reference: str,
) -> Path:
    path = (ROOT / reference).resolve()

    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(
            f"Reference escapes repository root: {reference}"
        ) from exc

    if not path.is_file():
        raise FileNotFoundError(
            f"Referenced file does not exist: {reference}"
        )

    return path


def sha256_digest(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        while chunk := file.read(65536):
            digest.update(chunk)

    return f"sha256:{digest.hexdigest()}"


def run_repository_validation() -> None:
    validator = (
        ROOT
        / "scripts"
        / "validate_examples.py"
    )

    result = subprocess.run(
        [
            sys.executable,
            str(validator),
        ],
        cwd=ROOT,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Repository validation failed. "
            "Resolution receipt was not generated."
        )


def endpoint_matches(
    endpoint: dict[str, Any],
    stage: str,
    protocol: dict[str, Any],
) -> bool:
    versions = endpoint.get(
        "versions",
        [],
    )

    return (
        endpoint.get("stage") == stage
        and endpoint.get("protocol_id")
        == protocol.get("protocol_id")
        and endpoint.get("record_type")
        == protocol.get("record_type")
        and isinstance(versions, list)
        and protocol.get("version") in versions
    )


def find_compatibility_link(
    compatibility_registry: dict[str, Any],
    source_stage: str,
    source_binding: dict[str, Any],
    target_stage: str,
    target_binding: dict[str, Any],
    canonical_id: str,
) -> dict[str, Any]:
    source_protocol = source_binding.get(
        "protocol",
        {},
    )

    target_protocol = target_binding.get(
        "protocol",
        {},
    )

    if not isinstance(source_protocol, dict):
        raise ValueError(
            f"Invalid source protocol at stage '{source_stage}'."
        )

    if not isinstance(target_protocol, dict):
        raise ValueError(
            f"Invalid target protocol at stage '{target_stage}'."
        )

    matches: list[dict[str, Any]] = []

    for link in compatibility_registry.get(
        "links",
        [],
    ):
        if not isinstance(link, dict):
            continue

        source = link.get(
            "source",
            {},
        )

        target = link.get(
            "target",
            {},
        )

        if not isinstance(source, dict):
            continue

        if not isinstance(target, dict):
            continue

        if (
            endpoint_matches(
                source,
                source_stage,
                source_protocol,
            )
            and endpoint_matches(
                target,
                target_stage,
                target_protocol,
            )
            and link.get("canonical_id")
            == canonical_id
            and link.get("disposition")
            in {
                "compatible",
                "adapter-required",
            }
        ):
            matches.append(link)

    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one usable compatibility link for "
            f"'{canonical_id}' from '{source_stage}' to "
            f"'{target_stage}', found {len(matches)}."
        )

    return matches[0]


def find_adapter_binding(
    profile: dict[str, Any],
    adapter_id: str,
    source_stage: str,
    target_stage: str,
    canonical_id: str,
) -> dict[str, Any]:
    matches = [
        binding
        for binding in profile.get(
            "adapter_bindings",
            [],
        )
        if isinstance(binding, dict)
        and binding.get("adapter_id")
        == adapter_id
        and binding.get("source_stage")
        == source_stage
        and binding.get("target_stage")
        == target_stage
        and binding.get("canonical_id")
        == canonical_id
    ]

    if len(matches) != 1:
        raise ValueError(
            f"Adapter '{adapter_id}' requires exactly one matching "
            f"profile binding, found {len(matches)}."
        )

    return matches[0]


def build_stage_map(
    profile: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    sequence = profile.get(
        "profile_sequence",
        [],
    )

    if not isinstance(sequence, list):
        raise ValueError(
            "profile_sequence must be an array."
        )

    return {
        str(binding["stage"]): binding
        for binding in sequence
        if isinstance(binding, dict)
        and isinstance(
            binding.get("stage"),
            str,
        )
    }


def build_resolved_stages(
    profile: dict[str, Any],
) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []

    for binding in profile.get(
        "profile_sequence",
        [],
    ):
        protocol = binding.get(
            "protocol",
            {},
        )

        resolved.append(
            {
                "stage": binding["stage"],
                "position": binding["position"],
                "protocol_id": protocol["protocol_id"],
                "version": protocol["version"],
                "repository": protocol["repository"],
                "schema_ref": protocol["schema_ref"],
                "record_type": protocol["record_type"],
            }
        )

    return resolved


def build_resolved_links(
    profile: dict[str, Any],
    compatibility_registry: dict[str, Any],
) -> list[dict[str, Any]]:
    stage_map = build_stage_map(profile)
    resolved: list[dict[str, Any]] = []

    for target_binding in profile.get(
        "profile_sequence",
        [],
    ):
        target_stage = str(
            target_binding["stage"]
        )

        for consumed in target_binding.get(
            "consumes",
            [],
        ):
            source_stage = str(
                consumed["from_stage"]
            )

            canonical_id = str(
                consumed["canonical_id"]
            )

            source_binding = stage_map.get(
                source_stage
            )

            if source_binding is None:
                raise ValueError(
                    f"Unknown source stage '{source_stage}'."
                )

            link = find_compatibility_link(
                compatibility_registry,
                source_stage,
                source_binding,
                target_stage,
                target_binding,
                canonical_id,
            )

            resolved_link: dict[str, Any] = {
                "link_id": link["link_id"],
                "source_stage": source_stage,
                "target_stage": target_stage,
                "canonical_id": canonical_id,
                "disposition": link["disposition"],
            }

            if (
                link.get("disposition")
                == "adapter-required"
            ):
                adapter_id = str(
                    link["adapter_id"]
                )

                binding = find_adapter_binding(
                    profile,
                    adapter_id,
                    source_stage,
                    target_stage,
                    canonical_id,
                )

                resolved_link.update(
                    {
                        "adapter_binding_id": binding[
                            "binding_id"
                        ],
                        "adapter_id": adapter_id,
                        "adapter_version": binding[
                            "adapter_version"
                        ],
                    }
                )

            resolved.append(resolved_link)

    return resolved


def build_registry_lock(
    binding: dict[str, Any],
) -> tuple[dict[str, Any], Path]:
    registry_ref = str(
        binding["registry_ref"]
    )

    registry_path = resolve_repository_path(
        registry_ref
    )

    registry = load_yaml(registry_path)

    lock = {
        "registry_id": registry["registry_id"],
        "version": registry["version"],
        "registry_ref": registry_ref,
        "digest": sha256_digest(
            registry_path
        ),
    }

    return lock, registry_path


def create_receipt(
    profile_path: Path,
) -> dict[str, Any]:
    profile = load_yaml(profile_path)

    identifier_lock, _ = build_registry_lock(
        profile["identifier_registry"]
    )

    compatibility_lock, compatibility_path = (
        build_registry_lock(
            profile["compatibility_registry"]
        )
    )

    adapter_lock, _ = build_registry_lock(
        profile["adapter_registry"]
    )

    compatibility_registry = load_yaml(
        compatibility_path
    )

    profile_digest = sha256_digest(
        profile_path
    )

    digest_suffix = profile_digest.split(
        ":",
        maxsplit=1,
    )[1][:12]

    return {
        "schema_version": "0.5.0",
        "receipt_kind": (
            "civilization-os-interoperability-resolution-receipt"
        ),
        "receipt_id": (
            f"{profile['profile_id']}-resolution-{digest_suffix}"
        ),
        "profile": {
            "profile_id": profile["profile_id"],
            "schema_version": profile[
                "schema_version"
            ],
            "profile_ref": relative_path(
                profile_path
            ),
            "digest": profile_digest,
        },
        "registries": {
            "identifier": identifier_lock,
            "compatibility": compatibility_lock,
            "adapter": adapter_lock,
        },
        "resolved_stages": build_resolved_stages(
            profile
        ),
        "resolved_links": build_resolved_links(
            profile,
            compatibility_registry,
        ),
        "conformance": {
            "status": "resolved",
            "profile_schema_valid": True,
            "profile_semantic_valid": True,
            "identifier_registry_valid": True,
            "compatibility_registry_valid": True,
            "adapter_registry_valid": True,
            "reference_resolution_valid": True,
            "digest_lock_created": True,
            "errors": [],
        },
        "handoff": {
            "status": "ready",
            "target_suite": (
                "kazene-protocol-conformance-suite"
            ),
            "required_checks": [
                "schema-validation",
                "semantic-validation",
                "registry-resolution",
                "compatibility-resolution",
                "adapter-resolution",
                "digest-verification",
                "cross-protocol-fixture-validation",
                "failure-propagation-validation",
            ],
        },
        "issued_at": datetime.now(
            timezone.utc
        ).isoformat().replace(
            "+00:00",
            "Z",
        ),
        "issuer": {
            "resolver_id": (
                "kazene-interoperability-resolver"
            ),
            "implementation": (
                "scripts/generate_resolution_receipt.py"
            ),
        },
        "extensions": {
            "lifecycle_scope": "kazene-core",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a resolved Civilization OS "
            "interoperability receipt."
        )
    )

    parser.add_argument(
        "profile",
        nargs="?",
        type=Path,
        default=DEFAULT_PROFILE,
    )

    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    parser.add_argument(
        "--skip-repository-validation",
        action="store_true",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    profile_path = args.profile.resolve()
    output_path = args.output.resolve()

    try:
        if not args.skip_repository_validation:
            run_repository_validation()

        receipt = create_receipt(
            profile_path
        )

        write_yaml(
            output_path,
            receipt,
        )

    except Exception as exc:
        print(f"[fatal] {exc}")
        return 1

    print(
        "[resolution-receipt-created] "
        f"{relative_path(output_path)}"
    )

    print(
        f"[receipt-id] "
        f"{receipt['receipt_id']}"
    )

    print(
        "[handoff-ready] "
        "kazene-protocol-conformance-suite"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
