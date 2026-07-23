from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]

PROFILE_SCHEMA_PATH = (
    ROOT
    / "schemas"
    / "civilization-os-interoperability-profile.schema.json"
)

REGISTRY_SCHEMA_PATH = (
    ROOT
    / "schemas"
    / "canonical-identifier-registry.schema.json"
)

REGISTRY_PATH = (
    ROOT
    / "registry"
    / "canonical-identifiers.yaml"
)

PASS_DIR = ROOT / "examples" / "pass"
FAIL_DIR = ROOT / "examples" / "fail"


EXPECTED_STAGES = (
    "origin",
    "trace",
    "authorization",
    "execution",
    "audit",
    "royalty",
)


REQUIRED_CONTRACTS = {
    "origin_id": (
        "origin",
        "origin_reference",
    ),
    "trace_id": (
        "trace",
        "trace_reference",
    ),
    "authorization_receipt_id": (
        "authorization",
        "authorization_receipt_reference",
    ),
    "execution_id": (
        "execution",
        "execution_reference",
    ),
    "audit_id": (
        "audit",
        "audit_reference",
    ),
    "allocation_id": (
        "royalty",
        "allocation_reference",
    ),
}


REQUIRED_LINKS = {
    "trace": (
        "origin",
        "origin_id",
    ),
    "authorization": (
        "trace",
        "trace_id",
    ),
    "execution": (
        "authorization",
        "authorization_receipt_id",
    ),
    "audit": (
        "execution",
        "execution_id",
    ),
    "royalty": (
        "audit",
        "audit_id",
    ),
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(
            f"{path.relative_to(ROOT)} must contain a JSON object."
        )

    return data


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(
            f"{path.relative_to(ROOT)} must contain a YAML object."
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
    validator = Draft202012Validator(schema)

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


def registry_semantic_errors(
    registry: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    identifiers = registry.get(
        "identifiers",
        [],
    )

    if not isinstance(identifiers, list):
        return [
            "identifiers must be an array."
        ]

    seen_ids: set[str] = set()

    for index, contract in enumerate(identifiers):
        if not isinstance(contract, dict):
            continue

        canonical_id = contract.get(
            "canonical_id"
        )

        if not isinstance(canonical_id, str):
            continue

        if canonical_id in seen_ids:
            errors.append(
                f"Identifier contract '{canonical_id}' "
                "appears more than once."
            )

        seen_ids.add(canonical_id)

    contracts_by_id = {
        contract.get("canonical_id"): contract
        for contract in identifiers
        if isinstance(contract, dict)
        and isinstance(
            contract.get("canonical_id"),
            str,
        )
    }

    for canonical_id, (
        expected_stage,
        expected_semantic_type,
    ) in REQUIRED_CONTRACTS.items():
        contract = contracts_by_id.get(
            canonical_id
        )

        if contract is None:
            errors.append(
                f"Required identifier contract "
                f"'{canonical_id}' is missing."
            )
            continue

        if (
            contract.get("producer_stage")
            != expected_stage
        ):
            errors.append(
                f"Identifier contract '{canonical_id}' "
                f"must use producer stage "
                f"'{expected_stage}'."
            )

        if (
            contract.get("semantic_type")
            != expected_semantic_type
        ):
            errors.append(
                f"Identifier contract '{canonical_id}' "
                f"must use semantic type "
                f"'{expected_semantic_type}'."
            )

        if contract.get("value_type") != "string":
            errors.append(
                f"Identifier contract '{canonical_id}' "
                "must use value_type 'string'."
            )

        if contract.get("cardinality") != "one":
            errors.append(
                f"Identifier contract '{canonical_id}' "
                "must use cardinality 'one'."
            )

    return errors


def build_contract_map(
    registry: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    identifiers = registry.get(
        "identifiers",
        [],
    )

    if not isinstance(identifiers, list):
        return {}

    return {
        contract["canonical_id"]: contract
        for contract in identifiers
        if isinstance(contract, dict)
        and isinstance(
            contract.get("canonical_id"),
            str,
        )
    }


def profile_semantic_errors(
    profile: dict[str, Any],
    registry: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    sequence = profile.get(
        "profile_sequence",
        [],
    )

    if not isinstance(sequence, list):
        return [
            "profile_sequence must be an array."
        ]

    registry_binding = profile.get(
        "identifier_registry",
        {},
    )

    if not isinstance(registry_binding, dict):
        return [
            "identifier_registry must be an object."
        ]

    if (
        registry_binding.get("registry_id")
        != registry.get("registry_id")
    ):
        errors.append(
            "Profile identifier_registry.registry_id "
            "does not match the loaded registry."
        )

    if (
        registry_binding.get("version")
        != registry.get("version")
    ):
        errors.append(
            "Profile identifier_registry.version "
            "does not match the loaded registry."
        )

    if (
        profile.get("identifier_namespace")
        != registry.get("namespace")
    ):
        errors.append(
            "Profile identifier_namespace "
            "does not match the registry namespace."
        )

    registry_ref = registry_binding.get(
        "registry_ref"
    )

    if isinstance(registry_ref, str):
        declared_registry_path = (
            ROOT
            / registry_ref
        ).resolve()

        if declared_registry_path != REGISTRY_PATH.resolve():
            errors.append(
                "identifier_registry.registry_ref "
                "does not resolve to the canonical registry."
            )

    actual_stages = tuple(
        binding.get("stage")
        for binding in sequence
        if isinstance(binding, dict)
    )

    if actual_stages != EXPECTED_STAGES:
        errors.append(
            "profile_sequence must follow this exact order: "
            + " -> ".join(EXPECTED_STAGES)
            + "."
        )

    stage_positions: dict[str, int] = {}
    produced_by_stage: dict[str, set[str]] = {}

    for index, binding in enumerate(sequence):
        if not isinstance(binding, dict):
            errors.append(
                f"profile_sequence[{index}] must be an object."
            )
            continue

        stage = binding.get("stage")
        position = binding.get("position")

        if stage not in EXPECTED_STAGES:
            continue

        if stage in stage_positions:
            errors.append(
                f"Stage '{stage}' appears more than once."
            )

        stage_positions[stage] = index

        expected_position = index + 1

        if position != expected_position:
            errors.append(
                f"Stage '{stage}' has position "
                f"{position}; expected "
                f"{expected_position}."
            )

        produced_ids: list[str] = []

        for output in binding.get(
            "produces",
            [],
        ):
            if not isinstance(output, dict):
                continue

            canonical_id = output.get(
                "canonical_id"
            )

            if isinstance(canonical_id, str):
                produced_ids.append(
                    canonical_id
                )

        if len(produced_ids) != len(
            set(produced_ids)
        ):
            errors.append(
                f"Stage '{stage}' produces "
                "duplicate canonical identifiers."
            )

        produced_by_stage[stage] = set(
            produced_ids
        )

    contract_map = build_contract_map(
        registry
    )

    global_producers: dict[str, str] = {}

    for stage, canonical_ids in (
        produced_by_stage.items()
    ):
        for canonical_id in canonical_ids:
            previous_stage = global_producers.get(
                canonical_id
            )

            if previous_stage is not None:
                errors.append(
                    f"Canonical ID '{canonical_id}' "
                    f"is produced by both "
                    f"'{previous_stage}' and '{stage}'."
                )
            else:
                global_producers[
                    canonical_id
                ] = stage

            contract = contract_map.get(
                canonical_id
            )

            if contract is None:
                errors.append(
                    f"Produced canonical ID "
                    f"'{canonical_id}' is not "
                    "registered."
                )
                continue

            declared_stage = contract.get(
                "producer_stage"
            )

            if declared_stage != stage:
                errors.append(
                    f"Identifier contract "
                    f"'{canonical_id}' declares "
                    f"producer '{declared_stage}', "
                    f"but the profile produces it "
                    f"at stage '{stage}'."
                )

    for index, binding in enumerate(sequence):
        if not isinstance(binding, dict):
            continue

        stage = binding.get("stage")

        if stage not in EXPECTED_STAGES:
            continue

        seen_inputs: set[
            tuple[str, str]
        ] = set()

        for item in binding.get(
            "consumes",
            [],
        ):
            if not isinstance(item, dict):
                continue

            source_stage = item.get(
                "from_stage"
            )

            canonical_id = item.get(
                "canonical_id"
            )

            link = (
                str(source_stage),
                str(canonical_id),
            )

            if link in seen_inputs:
                errors.append(
                    f"Stage '{stage}' consumes "
                    f"duplicate link "
                    f"'{source_stage}:{canonical_id}'."
                )

            seen_inputs.add(link)

            contract = contract_map.get(
                str(canonical_id)
            )

            if contract is None:
                errors.append(
                    f"Consumed canonical ID "
                    f"'{canonical_id}' is not "
                    "registered."
                )
            else:
                declared_stage = contract.get(
                    "producer_stage"
                )

                if declared_stage != source_stage:
                    errors.append(
                        f"Stage '{stage}' declares "
                        f"'{canonical_id}' from "
                        f"'{source_stage}', but its "
                        f"registry producer is "
                        f"'{declared_stage}'."
                    )

            source_position = stage_positions.get(
                str(source_stage)
            )

            if source_position is None:
                errors.append(
                    f"Stage '{stage}' references "
                    f"unknown source stage "
                    f"'{source_stage}'."
                )
                continue

            if source_position >= index:
                errors.append(
                    f"Stage '{stage}' consumes "
                    f"'{canonical_id}' from "
                    f"non-earlier stage "
                    f"'{source_stage}'."
                )

            source_outputs = (
                produced_by_stage.get(
                    str(source_stage),
                    set(),
                )
            )

            if canonical_id not in source_outputs:
                errors.append(
                    f"Stage '{stage}' consumes "
                    f"'{canonical_id}' from "
                    f"'{source_stage}', but that "
                    "stage does not produce it."
                )

    for canonical_id, (
        required_stage,
        _,
    ) in REQUIRED_CONTRACTS.items():
        if canonical_id not in (
            produced_by_stage.get(
                required_stage,
                set(),
            )
        ):
            errors.append(
                f"Stage '{required_stage}' "
                f"must produce canonical ID "
                f"'{canonical_id}'."
            )

    bindings_by_stage = {
        binding.get("stage"): binding
        for binding in sequence
        if isinstance(binding, dict)
    }

    for consumer_stage, (
        source_stage,
        canonical_id,
    ) in REQUIRED_LINKS.items():
        binding = bindings_by_stage.get(
            consumer_stage,
            {},
        )

        consumes = (
            binding.get("consumes", [])
            if isinstance(binding, dict)
            else []
        )

        has_required_link = any(
            isinstance(item, dict)
            and item.get("from_stage")
            == source_stage
            and item.get("canonical_id")
            == canonical_id
            and item.get("required") is True
            for item in consumes
        )

        if not has_required_link:
            errors.append(
                f"Stage '{consumer_stage}' "
                f"must require '{canonical_id}' "
                f"from stage '{source_stage}'."
            )

    return errors


def collect_yaml_files(
    directory: Path,
) -> list[Path]:
    return sorted(
        [
            *directory.glob("*.yaml"),
            *directory.glob("*.yml"),
        ]
    )


def validate_registry(
    registry: dict[str, Any],
    registry_schema: dict[str, Any],
) -> bool:
    print(
        f"[validate-registry] "
        f"{REGISTRY_PATH.relative_to(ROOT)}"
    )

    errors = schema_errors(
        registry,
        registry_schema,
    )

    if errors:
        for error in errors:
            print(
                f"[registry-schema-error] "
                f"{error}"
            )
        return False

    print("[registry-schema-ok]")

    errors = registry_semantic_errors(
        registry
    )

    if errors:
        for error in errors:
            print(
                f"[registry-semantic-error] "
                f"{error}"
            )
        return False

    print("[registry-semantic-ok]")

    return True


def validate_expected_pass(
    path: Path,
    profile_schema: dict[str, Any],
    registry: dict[str, Any],
) -> bool:
    print(
        f"[validate-pass] "
        f"{path.relative_to(ROOT)}"
    )

    try:
        profile = load_yaml(path)
    except Exception as exc:
        print(f"[yaml-error] {exc}")
        return False

    errors = schema_errors(
        profile,
        profile_schema,
    )

    if errors:
        for error in errors:
            print(
                f"[schema-error] {error}"
            )
        return False

    print("[schema-ok]")

    errors = profile_semantic_errors(
        profile,
        registry,
    )

    if errors:
        for error in errors:
            print(
                f"[semantic-error] {error}"
            )
        return False

    print("[semantic-ok]")

    return True


def validate_expected_fail(
    path: Path,
    profile_schema: dict[str, Any],
    registry: dict[str, Any],
) -> bool:
    print(
        f"[validate-fail] "
        f"{path.relative_to(ROOT)}"
    )

    try:
        profile = load_yaml(path)
    except Exception as exc:
        print(
            f"[expected-yaml-failure] "
            f"{exc}"
        )
        return True

    errors = schema_errors(
        profile,
        profile_schema,
    )

    if errors:
        for error in errors:
            print(
                f"[expected-schema-failure] "
                f"{error}"
            )
        return True

    errors = profile_semantic_errors(
        profile,
        registry,
    )

    if errors:
        for error in errors:
            print(
                f"[expected-semantic-failure] "
                f"{error}"
            )
        return True

    print(
        "[unexpected-pass] "
        "Failure example was accepted."
    )

    return False


def main() -> int:
    print(
        "=== Civilization OS "
        "Interoperability Profile Validation ==="
    )

    print(
        "profile schema: "
        f"{PROFILE_SCHEMA_PATH.relative_to(ROOT)}"
    )

    print(
        "registry schema: "
        f"{REGISTRY_SCHEMA_PATH.relative_to(ROOT)}"
    )

    print()

    try:
        profile_schema = load_json(
            PROFILE_SCHEMA_PATH
        )

        registry_schema = load_json(
            REGISTRY_SCHEMA_PATH
        )

        registry = load_yaml(
            REGISTRY_PATH
        )

        Draft202012Validator.check_schema(
            profile_schema
        )

        Draft202012Validator.check_schema(
            registry_schema
        )

    except Exception as exc:
        print(f"[fatal] {exc}")
        return 1

    success = validate_registry(
        registry,
        registry_schema,
    )

    print()

    pass_files = collect_yaml_files(
        PASS_DIR
    )

    fail_files = collect_yaml_files(
        FAIL_DIR
    )

    if not pass_files:
        print(
            "[fatal] No pass examples found."
        )
        return 1

    for path in pass_files:
        success = (
            validate_expected_pass(
                path,
                profile_schema,
                registry,
            )
            and success
        )

        print()

    for path in fail_files:
        success = (
            validate_expected_fail(
                path,
                profile_schema,
                registry,
            )
            and success
        )

        print()

    if success:
        print(
            "All registry and interoperability "
            "profile examples behaved as expected."
        )
        return 0

    print("Validation failed.")

    return 1


if __name__ == "__main__":
    sys.exit(main())
