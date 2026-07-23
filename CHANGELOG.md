# Changelog

All notable changes to this project are documented in this file.

The format is based on Keep a Changelog, and the project follows Semantic
Versioning where practical.

## [Unreleased]

### Planned

- Integration fixtures for `kazene-protocol-conformance-suite`.
- Resolution-receipt signing and verification.
- Registry revocation records.
- Remote protocol-package verification.
- Cross-protocol failure-propagation fixtures.
- Parallel and conditional profile research.

## [0.5.0] - 2026-07-23

### Added

- Interoperability Resolution Receipt schema.
- Resolution receipt generator.
- Resolution receipt validator.
- SHA-256 digest locking for:
  - interoperability profiles;
  - Canonical Identifier Registry;
  - Protocol Compatibility Registry;
  - Protocol Adapter Registry.
- Exact six-stage protocol snapshot.
- Resolved compatibility-link snapshot.
- Resolved adapter-binding snapshot.
- Machine-verifiable resolution status.
- Explicit conformance handoff to
  `kazene-protocol-conformance-suite`.
- Required downstream checks:
  - schema validation;
  - semantic validation;
  - registry resolution;
  - compatibility resolution;
  - adapter resolution;
  - digest verification;
  - cross-protocol fixture validation;
  - failure-propagation validation.
- Resolution policy requiring:
  - a resolution receipt;
  - digest locks;
  - an exact stage snapshot;
  - conformance-suite handoff.
- GitHub Actions receipt generation.
- GitHub Actions receipt validation.
- Workflow artifact upload for generated receipts.
- Repository-root path containment checks in receipt generation and
  verification.

### Changed

- Updated the interoperability profile schema to `0.5.0`.
- Added mandatory `resolution_policy`.
- Added mandatory conformance flags:
  - `require_resolution_receipt`;
  - `require_digest_lock`;
  - `require_conformance_handoff`.
- Updated all passing examples to the v0.5 profile format.
- Updated all expected-failure examples to pass v0.5 schema validation before
  reaching their intended semantic failures.
- Extended semantic validation to verify resolution and handoff policies.
- Completed the first interoperability lifecycle from ordered profile
  composition through immutable resolution evidence.

## [0.4.0] - 2026-07-23

### Added

- Protocol Adapter Registry.
- Protocol Adapter Registry JSON Schema.
- Explicit adapter contracts for cross-version protocol connections.
- Adapter identity and version declarations.
- Adapter lifecycle status:
  - `draft`;
  - `active`;
  - `deprecated`.
- Adapter source and target endpoints.
- Canonical identifier preservation across adapters.
- Field-level transformation operations:
  - `copy`;
  - `rename`;
  - `wrap`;
  - `unwrap`;
  - `serialize`;
  - `deserialize`.
- Adapter lossiness classifications:
  - `lossless`;
  - `conditionally-lossy`;
  - `lossy`.
- Adapter integrity behaviors:
  - `preserve`;
  - `recompute-digest`;
  - `re-sign`;
  - `none`.
- Profile-level adapter bindings.
- Explicit adapter-version binding.
- Adapter endpoint validation.
- Adapter canonical-identifier validation.
- Rejection of unknown adapters.
- Rejection of deprecated adapters in active compatibility links.
- Rejection of missing adapter bindings.
- Rejection of duplicate adapter bindings.
- Rejection of unused adapter bindings.
- Optional rejection of non-lossless adapters.
- Passing adapter-mediated profile using Trace Relay Protocol `v0.9`.
- Expected-failure example for a missing required adapter.

### Changed

- Updated the Protocol Compatibility Registry schema to `0.4.0`.
- Updated the Protocol Compatibility Registry document to `v0.4`.
- Replaced informal adapter references with registered `adapter_id` values.
- Added an adapter-required compatibility link between:
  - Trace Relay Protocol `v0.9`;
  - Action Authorization Receipt Protocol `v0.5`.
- Added direct Origin-to-Trace compatibility for Trace Relay Protocol `v0.9`.
- Extended the interoperability profile with:
  - `adapter_registry`;
  - `adapter_bindings`;
  - adapter-resolution conformance policies.
- Extended semantic validation to resolve adapter-required compatibility
  links against exact profile bindings.

## [0.3.0] - 2026-07-23

### Added

- Protocol Compatibility Registry.
- Protocol Compatibility Registry JSON Schema.
- Explicit source and target protocol endpoint contracts.
- Exact protocol-version compatibility declarations.
- Record-type compatibility declarations.
- Canonical-identifier compatibility binding.
- Compatibility dispositions:
  - `compatible`;
  - `adapter-required`;
  - `blocked`;
  - `deprecated`.
- Machine-verifiable compatibility resolution for each consumed canonical
  identifier.
- Rejection of unknown compatibility links.
- Rejection of ambiguous compatibility links.
- Rejection of blocked links.
- Rejection of deprecated links.
- Explicit blocked Execution-to-Royalty audit-bypass contract.
- Expected-failure example for a blocked direct Execution-to-Royalty
  connection.

### Changed

- Updated the interoperability profile schema to `0.3.0`.
- Added a mandatory `compatibility_registry` reference.
- Extended semantic validation to match:
  - lifecycle stages;
  - protocol identifiers;
  - protocol versions;
  - record types;
  - canonical identifiers.
- Replaced identifier-only connection assumptions with explicit compatibility
  contracts.
- Required every consumed identifier to resolve to a declared compatibility
  link.

## [0.2.0] - 2026-07-23

### Added

- Canonical Identifier Registry.
- Canonical Identifier Registry JSON Schema.
- Shared cross-protocol identifier contracts.
- Explicit canonical identifier ownership by producer stage.
- Identifier semantic-type declarations.
- Identifier value-type declarations.
- Identifier cardinality declarations.
- Identifier mutability declarations.
- Identifier integrity requirements.
- Core canonical identifier contracts:
  - `origin_id`;
  - `trace_id`;
  - `authorization_receipt_id`;
  - `execution_id`;
  - `audit_id`;
  - `allocation_id`.
- Profile-to-registry reference binding.
- Registry namespace validation.
- Registry identity and version validation.
- Rejection of unregistered produced identifiers.
- Rejection of unregistered consumed identifiers.
- Rejection of producer-stage conflicts.
- Expected-failure example for an unregistered `policy_id`.

### Changed

- Updated the interoperability profile schema to `0.2.0`.
- Replaced implicit identifier naming with explicit registry resolution.
- Extended semantic validation to validate the canonical registry before
  validating profile examples.
- Moved canonical identifier meaning out of individual profile declarations
  and into a shared registry.

## [0.1.0] - 2026-07-23

### Added

- Initial Civilization OS Interoperability Profile.
- Ordered Profile Binding model.
- Fixed six-stage lifecycle:
  - Origin;
  - Trace;
  - Authorization;
  - Execution;
  - Audit;
  - Royalty.
- External protocol reference model.
- Protocol repository references.
- Protocol schema references.
- Protocol record-type references.
- Canonical identifier production declarations.
- Canonical identifier consumption declarations.
- Local-field mappings.
- Required canonical lifecycle outputs:
  - `origin_id`;
  - `trace_id`;
  - `authorization_receipt_id`;
  - `execution_id`;
  - `audit_id`;
  - `allocation_id`.
- Required lifecycle links:
  - Origin to Trace;
  - Trace to Authorization;
  - Authorization to Execution;
  - Execution to Audit;
  - Audit to Royalty.
- Forward-only reference rule.
- Single-producer rule for canonical identifiers.
- Exact six-stage ordering rule.
- JSON Schema validation.
- Semantic validation script.
- Passing core lifecycle example.
- Expected-failure example for a future-stage reference.
- GitHub Actions validation workflow.
- Initial specification document.
- Initial README.
- Initial changelog.

### Design decision

- Independent protocols remain independently versioned.
- The repository defines protocol interconnection rather than merging all
  Civilization OS schemas into one monolithic specification.
