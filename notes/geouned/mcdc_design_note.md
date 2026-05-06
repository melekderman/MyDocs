# MCDC Design Note for GEOUNED

## Goal

Add MCDC as a new CAD-to-CSG export target in GEOUNED with the smallest possible change surface.

The first implementation should generate a valid MCDC Python geometry scaffold, not a fully simulation-ready transport deck.

## Scope

### In Scope

- add a new `mcdc` output format
- generate MCDC Python geometry output
- export surfaces
- export boolean cell regions
- export cells
- emit placeholder material bindings
- document supported and unsupported geometry cases

### Out of Scope for Phase 1

- full material physics generation
- automatic source definition
- automatic tally definition
- automatic run settings
- broad torus support

## Architecture Decision

MCDC support should be implemented as a new writer backend.

Why:

- GEOUNED already has the geometry it needs internally.
- format dispatch is already isolated in the writer layer.
- MCDC input is Python API based, so the closest existing template is the OpenMC Python writer.

This means the core CAD loading and decomposition pipeline should remain unchanged.

## Supported Geometry Strategy

| GEOUNED geometry | Phase 1 strategy |
| --- | --- |
| Plane | direct MCDC surface |
| Sphere | direct MCDC surface |
| Axis-aligned cylinder | direct MCDC surface |
| Arbitrary cylinder | export as quadric |
| Cone | export as direct cone or quadric fallback |
| Torus | add MCDC support |

## Key Constraint

GEOUNED currently stores:

- material id
- density
- material comment/info

MCDC expects full transport material data.

Therefore phase 1 should export placeholder materials only. A fully runnable MCDC input deck requires a separate material mapping layer.

## Main Implementation Changes

### New File

- `src/geouned/GEOUNED/write/mcdc_format.py`

Responsibilities:

- write imports
- write placeholder materials
- write surfaces
- write cells
- write optional commented templates for source, tally, settings, and `mcdc.run()`

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

## Writer-Layer Tasks

### 1. Extend Dispatch

In `write_files.py`:

- add `mcdc` to the supported format list
- import and call the new MCDC writer
- choose a non-conflicting output name

Recommended filename:

- `geometryName + ".mcdc.py"`

This avoids collision with the existing OpenMC Python output.

### 2. Add Surface Conversion

In `write/functions.py` add a helper such as:

- `mcdc_surface(...)`

This function should:

- map direct primitives to MCDC constructors
- use quadric fallback where needed
- raise a clear error for unsupported torus cases

### 3. Add Region Serialization

In `write/functions.py` add helpers such as:

- `write_mcdc_region(...)`
- `write_sequence_mcdc(...)`

The serializer should preserve:

- intersection
- union
- complement
- signed half-spaces

## Testing Strategy

### Update Existing Tests

Extend `tests/test_cadtocsg.py` to:

- expect the MCDC output file
- include `mcdc` in format loops
- verify folder creation for the new writer

### Add Narrow Writer Tests

Recommended targeted tests:

- arbitrary cylinder becomes quadric
- cone becomes direct or quadric output
- nested boolean region serialization is preserved
- torus fails with a clear message

## Risks

### API Drift

MCDC stable docs and current source are not perfectly aligned. GEOUNED should target a pinned MCDC version.

### Torus

Torus support is not stable enough for phase 1 and should not be approximated silently.

### Material Completeness

Without a separate material mapping layer, the output will be geometry-valid but not fully simulation-ready.

## Recommended Delivery Phases

### Phase 1

- geometry-only MCDC writer
- placeholder materials
- direct support for planes, spheres, cylinders
- cone support through direct or quadric output
- explicit torus rejection

### Phase 2

- version-pinned extended geometry support
- better diagnostics
- optional limited torus support if verified upstream

### Phase 3

- external material mapping
- source/tally/settings generation
- end-to-end MCDC validation

## Final Recommendation

Implement MCDC support as a new Python-writer backend, keep phase 1 geometry-focused, and defer full transport-material generation to a later design.
