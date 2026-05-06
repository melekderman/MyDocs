# MCDC Support Integration Report for GEOUNED

## Executive Summary

GEOUNED already converts STEP geometry into an internal constructive solid geometry representation and then dispatches that representation to format-specific writers. Because of that architecture, the cleanest path is to add a dedicated MCDC writer and extend the format dispatch layer, while leaving the CAD loading, decomposition, and surface detection pipelines unchanged.

The main technical constraints are:

- MCDC input is Python API based, not card-file based.
- GEOUNED currently stores geometry and lightweight material metadata, but not the transport data needed to build fully runnable MCDC materials.
- Some geometry support differs between MCDC stable documentation and the current MCDC source tree.
- Torus support is the highest-risk geometry area.

The recommended first milestone is not a fully runnable MCDC problem deck, but a geometry-focused MCDC Python input scaffold that exports:

- surfaces
- boolean cell regions
- cells
- placeholder material bindings

That first milestone should intentionally leave source, tally, setting, and detailed cross-section specification as user-completed or separately configured content.

## Current GEOUNED Architecture

### Conversion Flow

The relevant CAD-to-CSG export path is:

1. STEP geometry is loaded and interpreted into GEOUNED internal solids and surfaces.
2. GEOUNED builds a common internal CSG representation.
3. `CadToCsg.export_csg()` dispatches that representation to one or more format-specific writers.

The key entry points are:

- `src/geouned/GEOUNED/core.py`
- `src/geouned/GEOUNED/write/write_files.py`

### Current Output Format Dispatch

`write_geometry()` in `src/geouned/GEOUNED/write/write_files.py` is the central format router.

It currently supports:

- `mcnp`
- `openmc_xml`
- `openmc_py`
- `serpent`
- `phits`

This means MCDC support can be added by extending the same dispatch function with a new backend writer.

### Internal Geometry Types Already Available in GEOUNED

GEOUNED already detects and propagates these analytic surface types:

- Plane
- Cylinder
- Cone
- Sphere
- Torus

The relevant surface abstractions are defined in:

- `src/geouned/GEOUNED/utils/geometry_gu.py`
- `src/geouned/GEOUNED/utils/functions.py`

This is important because adding MCDC support does not require inventing new geometry primitives inside GEOUNED. The geometry data is already present.

## What MCDC Supports

## Stable Public API View

The stable MCDC documentation for `mcdc.surface()` clearly documents these surface categories:

- `plane-x`
- `plane-y`
- `plane-z`
- `plane`
- `cylinder-x`
- `cylinder-y`
- `cylinder-z`
- `sphere`
- `quadric`

From the stable public docs alone, the conservative interpretation is:

- planes are supported
- axis-aligned cylinders are supported
- spheres are supported
- arbitrary quadrics are supported

This already makes GEOUNED integration feasible for most of its geometry set because general cylinders and cones can be emitted as quadrics.

## Current MCDC Source Tree View

The current MCDC source tree goes further than the stable public surface reference and includes dedicated object constructors for:

- PlaneX, PlaneY, PlaneZ, Plane
- CylinderX, CylinderY, CylinderZ, Cylinder
- Sphere
- ConeX, ConeY, ConeZ
- Quadric
- TorusZ

The current source also supports boolean region construction using:

- unary `+surface`
- unary `-surface`
- region intersection with `&`
- region union with `|`
- region complement with `~`

That matters because GEOUNED cell definitions are not always simple flat half-space lists. They may contain nested AND/OR structures, so MCDC support is only practical if nested boolean region expressions can be preserved. The current MCDC source indicates that they can.

## Geometry Compatibility Matrix

The following matrix summarizes the geometry gap between GEOUNED and MCDC at the surface level.

| GEOUNED Surface | GEOUNED Status | MCDC Stable/Documented API | MCDC Current Source/Examples | Recommendation |
| --- | --- | --- | --- | --- |
| Plane | supported internally | supported | supported | required, direct support |
| Cylinder | supported internally | axis-aligned cylinders documented; general quadric path available | supported, including general cylinder support in source | required, direct where possible and quadric fallback otherwise |
| Cone | supported internally | not clearly exposed in the stable public surface list; quadric path available | supported in current source as axis-aligned cones | required, use direct support only if version-pinned, otherwise rely on quadric fallback |
| Sphere | supported internally | supported | supported | required, direct support |
| Torus | supported internally | not documented in the stable public API surface list | partially visible in current source as `TorusZ` | phase 1 should fail fast; optional later support only for verified target versions |

## Recommended Compatibility Interpretation

For GEOUNED integration planning, MCDC support should be split into three classes.

### Class A: Safe Direct Support

- Plane
- Sphere
- axis-aligned Cylinder

These should map directly to dedicated MCDC surface constructors.

### Class B: Safe Through Quadric Fallback

- arbitrary-axis Cylinder
- Cone

GEOUNED already computes general quadric coefficients for cylinders and cones. That means a reliable fallback exists even if direct MCDC constructors are version-dependent.

### Class C: High-Risk or Version-Dependent Support

- Torus

Torus is the least stable area.

Observations:

- GEOUNED internally supports torus surfaces.
- GEOUNED writers already restrict torus output to axis-aligned forms for some formats.
- stable MCDC documentation does not clearly advertise torus as part of the public `mcdc.surface()` API surface list.
- current MCDC source appears to expose `TorusZ`, but not a general torus family.

Recommended policy:

- phase 1: reject torus-containing models explicitly with a clear error message
- optional later phase: support only Z-axis torus if the target MCDC version is fixed and verified

## Geometry Mapping Strategy

The recommended GEOUNED-to-MCDC surface mapping is:

| GEOUNED Surface | MCDC Mapping Strategy | Risk |
| --- | --- | --- |
| Plane | direct plane constructor | low |
| Cylinder aligned to X/Y/Z | direct cylinder constructor | low |
| Cylinder arbitrary axis | `Quadric(...)` | low |
| Cone aligned to X/Y/Z | direct cone constructor if target MCDC version guarantees it | medium |
| Cone arbitrary axis | `Quadric(...)` | low |
| Sphere | direct sphere constructor | low |
| Torus aligned to Z | optional `TorusZ(...)` only if target MCDC version is pinned | high |
| Torus other orientations | unsupported in phase 1 | high |

## Why the Writer Layer Is the Right Integration Point

The current GEOUNED design already separates:

- geometry generation
- cell boolean construction
- output syntax generation

This makes MCDC support primarily a serialization problem.

No evidence from the current repository suggests that MCDC support would require changes to:

- STEP loading
- solid decomposition
- geometry recognition
- internal surface numbering

Those layers already deliver the information a new writer would need.

## Required Code Additions and Modifications

## 1. New Writer Module

Add a new writer module:

- `src/geouned/GEOUNED/write/mcdc_format.py`

This module should be modeled much more closely on `openmc_format.py` than on the MCNP, Serpent, or PHITS writers, because MCDC also builds geometry through a Python API.

The new writer should be responsible for:

- writing imports
- writing placeholder materials
- writing MCDC surfaces
- writing cell region expressions
- writing cells
- optionally writing commented template sections for source, tally, settings, and `mcdc.run()`

## 2. Extend Output Dispatch

Modify:

- `src/geouned/GEOUNED/write/write_files.py`

Required changes:

- add `mcdc` to `supported_mc_codes`
- import the new `McdcInput` writer class
- add a new dispatch branch for `mcdc`
- select a non-conflicting output filename

Important note:

`openmc_py` already writes to `.py`. MCDC is also Python-based, so writing another plain `.py` would create a filename conflict.

Recommended output naming options:

- `geometryName + ".mcdc.py"`
- `geometryName + "_mcdc.py"`

Using a unique suffix is strongly recommended.

## 3. Add MCDC Region Serialization

Modify:

- `src/geouned/GEOUNED/write/functions.py`

New functionality needed:

- `write_mcdc_region(...)`
- `write_sequence_mcdc(...)`
- possibly helper methods for converting GEOUNED boolean definitions into valid MCDC region expressions

This should be implemented analogously to the existing OpenMC Python region writer because both systems rely on programmatic boolean composition rather than flat card syntax.

The GEOUNED internal boolean model already supports nested regions, so the new serializer should preserve:

- intersection
- union
- complement
- signed half-spaces

## 4. Add MCDC Surface Conversion Function

Also in:

- `src/geouned/GEOUNED/write/functions.py`

Add a surface conversion helper such as:

- `mcdc_surface(...)`

It should:

- emit direct constructors for safe primitives
- fall back to `Quadric(...)` when needed
- fail clearly for unsupported torus cases

## 5. Update Public Export API Documentation

Modify:

- `src/geouned/GEOUNED/core.py`

Required updates:

- include `mcdc` in the documented `outFormat` choices
- optionally include `mcdc` in the default export tuple, depending on product policy

Recommended product decision:

- do not add `mcdc` to the default output list in the first PR unless the implementation is already mature and stable

That keeps the change lower-risk and avoids surprising users.

## 6. Tests to Update

Modify:

- `tests/test_cadtocsg.py`

Required updates:

- add the new MCDC suffix to expected output files
- add `mcdc` to the format lists used in conversion tests
- extend folder-creation tests for the new format

You will also likely want new MCDC-specific tests for:

- general cylinder emitted as quadric
- cone emitted as quadric or direct cone constructor
- nested boolean region serialization
- torus failure behavior

## 7. JSON Configuration Examples

Modify:

- `tests/config_cadtocsg_complete_defaults.json`

Potentially also update documentation examples so users can discover the new output format.

Minimal JSON currently does not include an `export_csg` block, so it does not require an `outFormat` update unless you decide to expand that file.

## 8. Documentation Files to Update

Modify:

- `docs/index.rst`
- `docs/example_of_use.rst`
- `docs/users_guide/execution_settings/cad2csg/python_cadtocsg_api_usage.rst`
- `docs/users_guide/execution_settings/cad2csg/python_cadtocsg_cli_usage.rst`
- `README.md`
- `pyproject.toml`

These locations currently describe the supported output codes and should be updated once MCDC support is merged.

## Files That Probably Do Not Need Changes

The following areas do not appear to require modification for a first implementation:

- `src/geouned/GEOUNED/conversion/*`
- `src/geouned/GEOUNED/decompose/*`
- `src/geouned/GEOUNED/loadfile/*`
- `src/geouned/GEOUNED/utils/geometry_gu.py`

In other words, MCDC support should be implemented without changing GEOUNED's internal geometry construction pipeline.

## Material Model Gap

This is the most important non-geometry limitation.

GEOUNED currently carries material metadata in a lightweight form:

- material id
- density
- material description text

This is sufficient for:

- MCNP labels
- PHITS labels
- Serpent/OpenMC placeholders

But it is not sufficient for a fully operational MCDC material definition.

MCDC expects transport-relevant material data, such as:

- capture
- scatter
- fission
- neutron yields
- spectra
- speed
- decay data where relevant

Therefore, a full MCDC deck requires one of these approaches.

### Option A: Geometry-Only Export

Generate geometry, cells, and placeholder materials, and leave transport data to the user.

This is the safest first version.

### Option B: External Material Mapping Layer

Introduce a new GEOUNED-side material mapping configuration that can translate material ids into full MCDC material constructor arguments.

This is the right long-term solution if MCDC is intended to be a first-class output target.

### Recommendation

Start with Option A.

## Region Semantics and Why They Matter

MCDC examples often show simple region lists such as:

- `[+s1, -s2]`

However, the current MCDC source model supports full boolean region objects with:

- `&`
- `|`
- `~`

This is critical because GEOUNED cell definitions can be nested expressions, not only flat conjunctions.

That means MCDC support is realistic without flattening GEOUNED definitions into a weaker representation.

## Recommended Implementation Phases

## Phase 1: Minimal Viable MCDC Geometry Export

Goal:

- generate a valid MCDC Python script scaffold

Include:

- imports
- placeholder material declarations
- surfaces
- cells
- comments for next user steps

Support:

- planes
- spheres
- cylinders
- cones via direct or quadric output
- nested boolean regions

Do not support yet:

- general torus handling
- automatic source definition
- automatic tally definition
- automatic simulation settings
- full material physics data

## Phase 2: Robust Surface Coverage

Add:

- explicit version-pinned cone path if needed
- verified torus policy
- stronger diagnostics for unsupported models

## Phase 3: First-Class MCDC Problem Generation

Add:

- external material mapping config
- optional source/tally/settings templates
- higher-quality end-to-end tests against a real MCDC environment

## Main Risks

### 1. API Version Drift in MCDC

The stable documentation and the current source tree are not perfectly aligned.

This means GEOUNED should target a specific MCDC version explicitly.

### 2. Torus Support

Torus is the least stable geometry area and should not be silently approximated.

### 3. Material Completeness

Without a new material mapping layer, MCDC export will not be fully simulation-ready.

### 4. Output Filename Collision

Because `openmc_py` already writes `.py`, MCDC must use a distinct filename convention.

## Recommended Initial PR Scope

The cleanest first pull request would do the following:

1. add a new `mcdc` output format
2. add `mcdc_format.py`
3. add MCDC surface and region serialization helpers
4. support planes, spheres, cylinders, and cones
5. fail explicitly on unsupported torus cases
6. emit placeholder materials
7. extend tests and user-facing documentation

That scope is small enough to review and safe enough to merge without overcommitting to a full transport-physics integration in the first step.

## Concrete File-Level Change List

### New Files

- `src/geouned/GEOUNED/write/mcdc_format.py`
- optionally `tests/test_mcdc_writer.py`

### Modified Files

- `src/geouned/GEOUNED/write/write_files.py`
- `src/geouned/GEOUNED/write/functions.py`
- `src/geouned/GEOUNED/core.py`
- `tests/test_cadtocsg.py`
- `tests/config_cadtocsg_complete_defaults.json`
- `docs/index.rst`
- `docs/example_of_use.rst`
- `docs/users_guide/execution_settings/cad2csg/python_cadtocsg_api_usage.rst`
- `docs/users_guide/execution_settings/cad2csg/python_cadtocsg_cli_usage.rst`
- `README.md`
- `pyproject.toml`

## Final Recommendation

MCDC support should be implemented in GEOUNED as a new Python-writer backend with clear scope boundaries.

The right first target is a geometry-valid MCDC script generator, not a fully complete transport input generator.

That approach matches GEOUNED's current architecture, minimizes implementation risk, and leaves room for a second-stage material integration design once the geometry export path is stable.
