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

IDENTIFIER_SCHEMA_PATH = (
    ROOT
    / "schemas"
    / "canonical-identifier-registry.schema.json"
)

COMPATIBILITY_SCHEMA_PATH = (
    ROOT
    / "schemas"
    / "protocol-compatibility-registry.schema.json"
)

IDENTIFIER_REGISTRY_PATH = (
    ROOT
    / "registry"
    / "canonical-identifiers.yaml"
)

COMPATIBILITY_REGISTRY_PATH = (
    ROOT
    / "registry"
    / "protocol-compatibility.yaml"
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

STAGE_POSITIONS = {
    stage: index
    for index, stage in enumerate(EXPECTED_STAGES)
}


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


def collect_yaml_files(directory: Path) -> list[Path]:
    return sorted(
        [
            *directory.glob("*.yaml"),
            *directory.glob("*.yml"),
        ]
    )


def build_identifier_contract_map(
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


def identifier_registry_semantic_errors(
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

    for contract in identifiers:
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

    contract_map = build_identifier_contract_map(
        registry
    )

    for canonical_id, (
        expected_stage,
        expected_semantic_type,
    ) in REQUIRED_CONTRACTS.items():
        contract = contract_map.get(
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


def compatibility_registry_semantic_errors(
    registry: dict[str, Any],
    identifier_registry: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    links = registry.get(
        "links",
        [],
    )

    if not isinstance(links, list):
        return [
            "links must be an array."
        ]

    identifier_contracts = (
        build_identifier_contract_map(
            identifier_registry
        )
    )

    seen_link_ids: set[str] = set()
    seen_contracts: set[
        tuple[
            str,
            str,
            str,
            str,
            str,
            str,
        ]
    ] = set()

    for index, link in enumerate(links):
        if not isinstance(link, dict):
            errors.append(
                f"links[{index}] must be an object."
            )
            continue

        link_id = link.get("link_id")

        if isinstance(link_id, str):
            if link_id in seen_link_ids:
                errors.append(
                    f"Compatibility link '{link_id}' "
                    "appears more than once."
                )

            seen_link_ids.add(link_id)

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

        source_stage = source.get("stage")
        target_stage = target.get("stage")
        canonical_id = link.get("canonical_id")

        source_position = STAGE_POSITIONS.get(
            str(source_stage)
        )

        target_position = STAGE_POSITIONS.get(
            str(target_stage)
        )

        if (
            source_position is not None
            and target_position is not None
            and source_position >= target_position
        ):
            errors.append(
                f"Compatibility link '{link_id}' "
                f"must point from an earlier stage; "
                f"received '{source_stage}' to "
                f"'{target_stage}'."
            )

        contract = identifier_contracts.get(
            str(canonical_id)
        )

        if contract is None:
            errors.append(
                f"Compatibility link '{link_id}' "
                f"uses unregistered canonical ID "
                f"'{canonical_id}'."
            )
        elif (
            contract.get("producer_stage")
            != source_stage
        ):
            errors.append(
                f"Compatibility link '{link_id}' "
                f"uses '{canonical_id}' from "
                f"'{source_stage}', but the identifier "
                f"registry assigns its producer to "
                f"'{contract.get('producer_stage')}'."
            )

        contract_key = (
            str(source_stage),
            str(source.get("protocol_id")),
            str(source.get("record_type")),
            str(target_stage),
            str(target.get("protocol_id")),
            str(canonical_id),
        )

        if contract_key in seen_contracts:
            errors.append(
                f"Compatibility contract for "
                f"'{canonical_id}' from "
                f"'{source_stage}' to "
                f"'{target_stage}' is duplicated."
            )

        seen_contracts.add(contract_key)

    return errors


def registry_binding_errors(
    profile: dict[str, Any],
    profile_field: str,
    registry: dict[str, Any],
    registry_path: Path,
) -> list[str]:
    errors: list[str] = []

    binding = profile.get(
        profile_field,
        {},
    )

    if not isinstance(binding, dict):
        return [
            f"{profile_field} must be an object."
        ]

    if (
        binding.get("registry_id")
        != registry.get("registry_id")
    ):
        errors.append(
            f"{profile_field}.registry_id "
            "does not match the loaded registry."
        )

    if (
        binding.get("version")
        != registry.get("version")
    ):
        errors.append(
            f"{profile_field}.version "
            "does not match the loaded registry."
        )

    registry_ref = binding.get(
        "registry_ref"
    )

    if isinstance(registry_ref, str):
        declared_path = (
            ROOT
            / registry_ref
        ).resolve()

        if declared_path != registry_path.resolve():
            errors.append(
                f"{profile_field}.registry_ref "
                "does not resolve to the expected registry."
            )

    return errors


def protocol_summary(
    stage: str,
    binding: dict[str, Any],
) -> str:
    protocol = binding.get(
        "protocol",
        {},
    )

    if not isinstance(protocol, dict):
        return f"{stage}:<invalid-protocol>"

    return (
        f"{stage}:"
        f"{protocol.get('protocol_id')}"
        f"@{protocol.get('version')}"
        f"/{protocol.get('record_type')}"
    )


def matching_compatibility_links(
    compatibility_registry: dict[str, Any],
    source_stage: str,
    source_binding: dict[str, Any],
    target_stage: str,
    target_binding: dict[str, Any],
    canonical_id: str,
) -> list[dict[str, Any]]:
    source_protocol = source_binding.get(
        "protocol",
        {},
    )

    target_protocol = target_binding.get(
        "protocol",
        {},
    )

    if not isinstance(source_protocol, dict):
        return []

    if not isinstance(target_protocol, dict):
        return []

    links = compatibility_registry.get(
        "links",
        [],
    )

    if not isinstance(links, list):
        return []

    matches: list[dict[str, Any]] = []

    for link in links:
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

        source_versions = source.get(
            "versions",
            [],
        )

        target_versions = target.get(
            "versions",
            [],
        )

        if not isinstance(source_versions, list):
            continue

        if not isinstance(target_versions, list):
            continue

        if (
            source.get("stage") == source_stage
            and source.get("protocol_id")
            == source_protocol.get("protocol_id")
            and source.get("record_type")
            == source_protocol.get("record_type")
            and source_protocol.get("version")
            in source_versions
            and target.get("stage") == target_stage
            and target.get("protocol_id")
            == target_protocol.get("protocol_id")
            and target.get("record_type")
            == target_protocol.get("record_type")
            and target_protocol.get("version")
            in target_versions
            and link.get("canonical_id")
            == canonical_id
        ):
            matches.append(link)

    return matches


def profile_semantic_errors(
    profile: dict[str, Any],
    identifier_registry: dict[str, Any],
    compatibility_registry: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    errors.extend(
        registry_binding_errors(
            profile,
            "identifier_registry",
            identifier_registry,
            IDENTIFIER_REGISTRY_PATH,
        )
    )

    errors.extend(
        registry_binding_errors(
            profile,
            "compatibility_registry",
            compatibility_registry,
            COMPATIBILITY_REGISTRY_PATH,
        )
    )

    if (
        profile.get("identifier_namespace")
        != identifier_registry.get("namespace")
    ):
        errors.append(
            "Profile identifier_namespace does not "
            "match the identifier registry namespace."
        )

    if (
        profile.get("identifier_namespace")
        != compatibility_registry.get("namespace")
    ):
        errors.append(
            "Profile identifier_namespace does not "
            "match the compatibility registry namespace."
        )

    sequence = profile.get(
        "profile_sequence",
        [],
    )

    if not isinstance(sequence, list):
        return errors + [
            "profile_sequence must be an array."
        ]

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

    bindings_by_stage: dict[
        str,
        dict[str, Any],
    ] = {}

    produced_by_stage: dict[
        str,
        set[str],
    ] = {}

    for index, binding in enumerate(sequence):
        if not isinstance(binding, dict):
            errors.append(
                f"profile_sequence[{index}] "
                "must be an object."
            )
            continue

        stage = binding.get("stage")
        position = binding.get("position")

        if stage not in EXPECTED_STAGES:
            continue

        stage_name = str(stage)

        if stage_name in bindings_by_stage:
            errors.append(
                f"Stage '{stage_name}' "
                "appears more than once."
            )

        bindings_by_stage[stage_name] = binding

        expected_position = index + 1

        if position != expected_position:
            errors.append(
                f"Stage '{stage_name}' has position "
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
                f"Stage '{stage_name}' produces "
                "duplicate canonical identifiers."
            )

        produced_by_stage[stage_name] = set(
            produced_ids
        )

    identifier_contracts = (
        build_identifier_contract_map(
            identifier_registry
        )
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

            contract = identifier_contracts.get(
                canonical_id
            )

            if contract is None:
                errors.append(
                    f"Produced canonical ID "
                    f"'{canonical_id}' is not registered."
                )
                continue

            declared_stage = contract.get(
                "producer_stage"
            )

            if declared_stage != stage:
                errors.append(
                    f"Identifier contract "
                    f"'{canonical_id}' declares producer "
                    f"'{declared_stage}', but the profile "
                    f"produces it at stage '{stage}'."
                )

    for target_index, binding in enumerate(sequence):
        if not isinstance(binding, dict):
            continue

        target_stage = binding.get("stage")

        if target_stage not in EXPECTED_STAGES:
            continue

        target_stage_name = str(
            target_stage
        )

        seen_inputs: set[
            tuple[str, str]
        ] = set()

        for item in binding.get(
            "consumes",
            [],
        ):
            if not isinstance(item, dict):
                continue

            source_stage = str(
                item.get("from_stage")
            )

            canonical_id = str(
                item.get("canonical_id")
            )

            link_key = (
                source_stage,
                canonical_id,
            )

            if link_key in seen_inputs:
                errors.append(
                    f"Stage '{target_stage_name}' "
                    f"consumes duplicate link "
                    f"'{source_stage}:{canonical_id}'."
                )

            seen_inputs.add(link_key)

            identifier_contract = (
                identifier_contracts.get(
                    canonical_id
                )
            )

            if identifier_contract is None:
                errors.append(
                    f"Consumed canonical ID "
                    f"'{canonical_id}' is not registered."
                )
            elif (
                identifier_contract.get(
                    "producer_stage"
                )
                != source_stage
            ):
                errors.append(
                    f"Stage '{target_stage_name}' "
                    f"declares '{canonical_id}' from "
                    f"'{source_stage}', but its registry "
                    f"producer is "
                    f"'{identifier_contract.get('producer_stage')}'."
                )

            source_position = (
                STAGE_POSITIONS.get(
                    source_stage
                )
            )

            if source_position is None:
                errors.append(
                    f"Stage '{target_stage_name}' "
                    f"references unknown source stage "
                    f"'{source_stage}'."
                )
                continue

            if source_position >= target_index:
                errors.append(
                    f"Stage '{target_stage_name}' "
                    f"consumes '{canonical_id}' from "
                    f"non-earlier stage "
                    f"'{source_stage}'."
                )

            source_outputs = (
                produced_by_stage.get(
                    source_stage,
                    set(),
                )
            )

            if canonical_id not in source_outputs:
                errors.append(
                    f"Stage '{target_stage_name}' "
                    f"consumes '{canonical_id}' from "
                    f"'{source_stage}', but that stage "
                    "does not produce it."
                )

            source_binding = (
                bindings_by_stage.get(
                    source_stage
                )
            )

            if source_binding is None:
                continue

            matches = (
                matching_compatibility_links(
                    compatibility_registry,
                    source_stage,
                    source_binding,
                    target_stage_name,
                    binding,
                    canonical_id,
                )
            )

            if not matches:
                errors.append(
                    f"No compatibility contract for "
                    f"'{canonical_id}' from "
                    f"{protocol_summary(source_stage, source_binding)} "
                    f"to "
                    f"{protocol_summary(target_stage_name, binding)}."
                )
                continue

            compatible_matches = [
                match
                for match in matches
                if match.get("disposition")
                == "compatible"
            ]

            if not compatible_matches:
                dispositions = sorted(
                    {
                        str(
                            match.get(
                                "disposition"
                            )
                        )
                        for match in matches
                    }
                )

                link_ids = sorted(
                    {
                        str(
                            match.get(
                                "link_id"
                            )
                        )
                        for match in matches
                    }
                )

                errors.append(
                    f"Compatibility for "
                    f"'{canonical_id}' from "
                    f"'{source_stage}' to "
                    f"'{target_stage_name}' is not "
                    f"usable; dispositions: "
                    f"{', '.join(dispositions)}; "
                    f"contracts: "
                    f"{', '.join(link_ids)}."
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
                f"Stage '{required_stage}' must "
                f"produce canonical ID "
                f"'{canonical_id}'."
            )

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


def validate_registry(
    label: str,
    path: Path,
    registry: dict[str, Any],
    schema: dict[str, Any],
    semantic_validator: Any,
) -> bool:
    print(
        f"[validate-{label}] "
        f"{path.relative_to(ROOT)}"
    )

    errors = schema_errors(
        registry,
        schema,
    )

    if errors:
        for error in errors:
            print(
                f"[{label}-schema-error] "
                f"{error}"
            )
        return False

    print(
        f"[{label}-schema-ok]"
    )

    errors = semantic_validator(
        registry
    )

    if errors:
        for error in errors:
            print(
                f"[{label}-semantic-error] "
                f"{error}"
            )
        return False

    print(
        f"[{label}-semantic-ok]"
    )

    return True


def validate_expected_pass(
    path: Path,
    profile_schema: dict[str, Any],
    identifier_registry: dict[str, Any],
    compatibility_registry: dict[str, Any],
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
        identifier_registry,
        compatibility_registry,
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
    identifier_registry: dict[str, Any],
    compatibility_registry: dict[str, Any],
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
        identifier_registry,
        compatibility_registry,
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
        "identifier schema: "
        f"{IDENTIFIER_SCHEMA_PATH.relative_to(ROOT)}"
    )

    print(
        "compatibility schema: "
        f"{COMPATIBILITY_SCHEMA_PATH.relative_to(ROOT)}"
    )

    print()

    try:
        profile_schema = load_json(
            PROFILE_SCHEMA_PATH
        )

        identifier_schema = load_json(
            IDENTIFIER_SCHEMA_PATH
        )

        compatibility_schema = load_json(
            COMPATIBILITY_SCHEMA_PATH
        )

        identifier_registry = load_yaml(
            IDENTIFIER_REGISTRY_PATH
        )

        compatibility_registry = load_yaml(
            COMPATIBILITY_REGISTRY_PATH
        )

        Draft202012Validator.check_schema(
            profile_schema
        )

        Draft202012Validator.check_schema(
            identifier_schema
        )

        Draft202012Validator.check_schema(
            compatibility_schema
        )

    except Exception as exc:
        print(f"[fatal] {exc}")
        return 1

    success = validate_registry(
        "identifier-registry",
        IDENTIFIER_REGISTRY_PATH,
        identifier_registry,
        identifier_schema,
        identifier_registry_semantic_errors,
    )

    print()

    compatibility_validator = (
        lambda registry: (
            compatibility_registry_semantic_errors(
                registry,
                identifier_registry,
            )
        )
    )

    success = (
        validate_registry(
            "compatibility-registry",
            COMPATIBILITY_REGISTRY_PATH,
            compatibility_registry,
            compatibility_schema,
            compatibility_validator,
        )
        and success
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
                identifier_registry,
                compatibility_registry,
            )
            and success
        )

        print()

    for path in fail_files:
        success = (
            validate_expected_fail(
                path,
                profile_schema,
                identifier_registry,
                compatibility_registry,
            )
            and success
        )

        print()

    if success:
        print(
            "All registries and interoperability "
            "profile examples behaved as expected."
        )
        return 0

    print("Validation failed.")

    return 1


if __name__ == "__main__":
    sys.exit(main())
