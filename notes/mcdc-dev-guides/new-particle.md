# Adding a New Particle Type to MC/DC: A Developer's Guide

*Based on the electron transport implementation in the `Feb23` branch.*

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture and Design Philosophy](#2-architecture-and-design-philosophy)
3. [Step-by-Step Implementation Checklist](#3-step-by-step-implementation-checklist)
4. [Step 1 — Define a Particle Type Constant](#4-step-1--define-a-particle-type-constant)
5. [Step 2 — Extend the Particle Data Structure](#5-step-2--extend-the-particle-data-structure)
6. [Step 3 — Define Physics Data Objects](#6-step-3--define-physics-data-objects)
7. [Step 4 — Define Reaction Classes](#7-step-4--define-reaction-classes)
8. [Step 5 — Write Auto-Generated Accessor Functions](#8-step-5--write-auto-generated-accessor-functions)
9. [Step 6 — Implement the Physics Module](#9-step-6--implement-the-physics-module)
10. [Step 7 — Wire into the Physics Dispatcher](#10-step-7--wire-into-the-physics-dispatcher)
11. [Step 8 — Extend the Source Definition](#11-step-8--extend-the-source-definition)
12. [Step 9 — Add New Tally Scores if Needed](#12-step-9--add-new-tally-scores-if-needed)
13. [Step 10 — Write Regression Tests](#13-step-10--write-regression-tests)
14. [Key Design Patterns and Conventions](#14-key-design-patterns-and-conventions)
15. [Physics Concepts You Must Understand Before Starting](#15-physics-concepts-you-must-understand-before-starting)
16. [Reference: Electron vs. Neutron Comparison Table](#16-reference-electron-vs-neutron-comparison-table)
17. [Common Pitfalls](#17-common-pitfalls)
18. [Nuclear Data and Cross-Section Libraries](#18-nuclear-data-and-cross-section-libraries)

---

## 1. Overview

MC/DC is a Monte Carlo radiation transport code written in Python with
Numba-JIT compilation for performance. Its original particle is the
**neutron**. The `Feb23` branch adds **electrons** as a fully supported
second particle species. This document uses that implementation as a
complete worked example of how to add *any* new particle type (proton,
photon, positron, muon, etc.) to MC/DC.

The high-level recipe is:

1. Assign a unique integer constant to your particle.
2. Add a `particle_type` discriminator field to the shared particle data
   structure.
3. Create a physics data carrier object (analogous to `Element` for
   electrons or `Nuclide` for neutrons).
4. Create reaction data classes for each interaction type.
5. Write auto-generated Numba-compatible accessor functions.
6. Implement the actual physics kernels (speed, cross-sections,
   collision handlers).
7. Route all calls through the central physics dispatcher.
8. Extend the `Source` class to emit your new particle type.
9. Add any new tally scores.
10. Validate with regression tests.

---

## 2. Architecture and Design Philosophy

### 2.1 Layered Structure

```
User input (mcdc.source, mcdc.Material, ...)
        │
        ▼
Object layer  (object_/*.py)
  ParticleData, Material, Element/Nuclide, Reaction*, Source, Settings
        │
        ▼
Physics dispatcher  (transport/physics/interface.py)
  particle_speed(), macro_xs(), collision_distance(), collision()
        │
   ┌────┴─────┐
   ▼          ▼
neutron/    electron/          ← one sub-package per particle type
native.py   native.py
        │
        ▼
Accessor layer  (mcdc_get/*.py, mcdc_set/*.py)
  Numba-compiled thin wrappers around structured numpy arrays
        │
        ▼
Simulation loop  (transport/simulation.py)
  step_particle() — calls dispatcher, scores tallies, manages banks
```

### 2.2 Key Constraints

- All hot-path code runs under **Numba `@njit`**. This means:
  - No Python objects or dynamic dispatch at runtime.
  - All data must live in structured NumPy arrays accessible by index.
  - New reaction or element data must be compiled into typed arrays before
    the JIT compilation step.
- Physics modules are **isolated sub-packages**. Each particle type lives
  under `transport/physics/<particle_type>/`. They never import each
  other.
- The **dispatcher** (`transport/physics/interface.py`) is the only place
  that knows which particle type is being transported. It inspects
  `particle["particle_type"]` and calls the appropriate sub-package.

---

## 3. Step-by-Step Implementation Checklist

| # | Task | File(s) |
|---|------|---------|
| 1 | Define integer constant | `mcdc/constant.py` |
| 2 | Add `particle_type` field | `mcdc/object_/particle.py` |
| 3 | Create physics data carrier object | `mcdc/object_/<carrier>.py` |
| 4 | Create reaction dataclasses | `mcdc/object_/reaction.py` |
| 5 | Write accessor functions | `mcdc/mcdc_get/<carrier>.py`, `mcdc/mcdc_set/<carrier>.py` |
| 6 | Implement physics module | `mcdc/transport/physics/<particle>/native.py` |
| 7 | Wire dispatcher | `mcdc/transport/physics/interface.py` |
| 8 | Extend Source | `mcdc/object_/source.py` |
| 9 | Add tally scores | `mcdc/constant.py`, `mcdc/transport/tally/score.py` |
| 10 | Write regression tests | `test/regression/<particle>_tests/` |

---

## 4. Step 1 — Define a Particle Type Constant

**File**: `mcdc/constant.py`

Every particle type is identified at runtime by a small non-negative
integer stored directly in the particle data structure. The neutron and
electron constants are:

```python
# mcdc/constant.py  (relevant excerpt)

# --- Particle types ---
PARTICLE_NEUTRON  = 0
PARTICLE_ELECTRON = 1
# Add yours here, e.g.:
# PARTICLE_PHOTON   = 2
# PARTICLE_PROTON   = 3
```

You should also add any particle-specific physical constants here. For
the electron these included:

```python
# Physical constants (SI-consistent, but energy in eV, length in cm)
ELECTRON_MASS            = 510.99895069e3   # eV/c²  (rest mass energy)
ELECTRON_CUTOFF_ENERGY   = 100.0            # eV — below this energy the
                                            # particle is killed
FINE_STRUCTURE_CONSTANT  = 7.2973525693e-3  # α ≈ 1/137
LIGHT_SPEED              = 2.99792458e10    # cm/s

# --- Reaction type integers for the new particle ---
REACTION_ELECTRON_ELASTIC_SCATTERING = 101
REACTION_ELECTRON_ELASTIC_SMALL_ANGLE = 102
REACTION_ELECTRON_ELASTIC_LARGE_ANGLE = 103
REACTION_ELECTRON_IONIZATION          = 104
REACTION_ELECTRON_BREMSSTRAHLUNG      = 105
REACTION_ELECTRON_EXCITATION          = 106
```

**Design rule**: All magic numbers that appear in physics kernels must be
named constants defined here. Reaction type integers must be globally
unique across all particle types.

---

## 5. Step 2 — Extend the Particle Data Structure

**File**: `mcdc/object_/particle.py`

The shared particle data structure is a NumPy structured array
(implemented as a dataclass that gets serialized to a NumPy dtype). Every
field must be a fixed-size primitive type — no Python objects.

The key addition for multi-particle support is:

```python
# mcdc/object_/particle.py

@dataclass
class ParticleData(ObjectBase):
    x:   float = 0.0   # Position
    y:   float = 0.0
    z:   float = 0.0
    t:   float = 0.0   # Time
    ux:  float = 0.0   # Direction cosines (unit vector)
    uy:  float = 0.0
    uz:  float = 0.0
    g:   int   = -1    # Energy group index (multigroup mode; -1 = CE mode)
    E:   float = 0.0   # Energy [eV]
    w:   float = 0.0   # Statistical weight
    particle_type: int = PARTICLE_NEUTRON   # ← THE DISCRIMINATOR FIELD
    rng_seed: uint = 0                      # Per-particle RNG state
    ...
```

The field `particle_type` is what every dispatcher function checks to
decide which physics sub-package to call. When you add a new particle
type, you do **not** need to add new fields to this struct (unless your
particle needs completely novel state, e.g., spin). The existing fields
`E`, `ux/uy/uz`, `w`, `x/y/z/t` are sufficient for most particles.

The `particle.py` file in `transport/particle.py` contains helper
functions (`move()`, `copy()`, `copy_as_child()`) that operate on this
structure. They are particle-type-agnostic, so you generally do not need
to modify them.

---

## 6. Step 3 — Define Physics Data Objects

**File**: `mcdc/object_/element.py` (for electrons) — you will create an
analogous file.

For neutrons the "physics carrier" is the `Nuclide` class, which loads
ENDF-format cross-section data. For electrons it is the `Element` class,
which loads EEDL-format data from HDF5 files.

Your new carrier object must:

1. Accept user-facing configuration (element/nuclide name, density, etc.)
2. Locate and load cross-section data from the library path (set via
   `MCDC_LIB` environment variable or a configuration file).
3. Store data as NumPy arrays that can be serialized into a global data
   block that Numba can access.

The `Element` class structure (simplified):

```python
# mcdc/object_/element.py  (simplified)

class Element:
    def __init__(self, name: str, density_atoms_per_barn_cm: float):
        self.name = name
        self.density = density_atoms_per_barn_cm

        # Load HDF5 file: $MCDC_LIB/{name}.h5
        path = Path(os.environ["MCDC_LIB"]) / f"{name}.h5"
        with h5py.File(path, "r") as f:
            # 1-D energy grid shared by all cross-section tables
            self.xs_energy_grid = f["energy_grid"][:]        # shape (N,)

            # Macroscopic cross-sections on that grid
            self.total_xs              = f["total_xs"][:]    # shape (N,)
            self.ionization_xs         = f["ionization_xs"][:]
            self.elastic_xs            = f["elastic_xs"][:]
            self.excitation_xs         = f["excitation_xs"][:]
            self.bremsstrahlung_xs     = f["bremsstrahlung_xs"][:]

            # Reaction-specific data (angles, energy distributions, subshells)
            self.ionization_reactions  = [
                ReactionElectronIonization(f["ionization"][i])
                for i in range(f["ionization"].attrs["count"])
            ]
            self.elastic_scattering_reactions = [...]
            self.excitation_reactions  = [...]
            self.bremsstrahlung_reactions = [...]
```

**Important**: The data stored in your carrier object must ultimately be
flattened into NumPy structured arrays before Numba compilation. The
`mcdc_get` and `mcdc_set` accessors (Step 5) provide the bridge between
the Python object and Numba-compiled code.

### Material integration

**File**: `mcdc/object_/material.py`

The `Material` class must be extended to accept your new carrier objects:

```python
# mcdc/object_/material.py  (simplified excerpt)

class Material:
    def __init__(self,
                 nuclide_composition: dict = None,    # neutrons
                 element_composition: dict = None,    # electrons ← added
                 # your_particle_composition: dict = None,
                 ):
        ...
        if element_composition is not None:
            self.elements = [
                Element(name, density)
                for name, density in element_composition.items()
            ]
```

The two composition modes are **mutually exclusive** in the current
implementation. If you add a third particle type, consider whether a
material can simultaneously contain nuclides (for neutrons) and elements
(for electrons). For photons transporting in the same geometry as
neutrons this becomes relevant.

---

## 7. Step 4 — Define Reaction Classes

**File**: `mcdc/object_/reaction.py`

Each distinct interaction mechanism gets its own class. These classes are
thin data containers — they load the reaction-specific physics tables from
an HDF5 group and store them as NumPy arrays.

For electrons, four reaction classes were added. Here is the ionization
class as a complete example:

```python
# mcdc/object_/reaction.py  (excerpt)

class ReactionElectronIonization:
    """
    Stores data for one subshell ionization channel.
    Loaded from HDF5 group f["ionization"][i].
    """
    def __init__(self, hdf5_group):
        # Binding energy of this subshell [eV]
        self.binding_energy = hdf5_group.attrs["binding_energy"]

        # Secondary (delta) electron energy distribution
        # Stored as a multi-table: one PDF per incident energy bin
        energy_grid   = hdf5_group["energy_grid"][:]       # (N_E,)
        delta_energies = hdf5_group["delta_energies"][:]   # (N_E, N_delta)
        pdf            = hdf5_group["pdf"][:]              # (N_E, N_delta)
        cdf            = hdf5_group["cdf"][:]              # (N_E, N_delta)
        self.delta_distribution = DistributionMultiTable(
            energy_grid, delta_energies, pdf, cdf
        )

class ReactionElectronElasticScattering:
    """Stores large-angle elastic scattering angular distribution tables."""
    def __init__(self, hdf5_group):
        self.energy_grid = hdf5_group["energy_grid"][:]
        self.mu_grid     = hdf5_group["mu_grid"][:]   # (N_E, N_mu)
        self.cdf         = hdf5_group["cdf"][:]       # (N_E, N_mu)

class ReactionElectronExcitation:
    """Stores energy loss (stopping power) tables for excitation."""
    def __init__(self, hdf5_group):
        self.energy_grid = hdf5_group["energy_grid"][:]
        self.eloss       = hdf5_group["eloss"][:]   # mean energy loss per event

class ReactionElectronBremsstrahlung:
    """Stores photon energy distribution for bremsstrahlung emission."""
    def __init__(self, hdf5_group):
        self.energy_grid   = hdf5_group["energy_grid"][:]
        self.photon_energies = hdf5_group["photon_energies"][:]
        self.pdf           = hdf5_group["pdf"][:]
        self.cdf           = hdf5_group["cdf"][:]
```

**Naming convention**: Prefix all electron reaction classes with
`ReactionElectron`. For protons, use `ReactionProton`, and so on.

---

## 8. Step 5 — Write Auto-Generated Accessor Functions

**Files**: `mcdc/mcdc_get/<carrier>.py`, `mcdc/mcdc_set/<carrier>.py`

Numba-compiled functions cannot call Python methods on objects — they can
only operate on primitive types and NumPy arrays. The accessor layer
provides Numba-compatible functions that retrieve individual fields or
slices from the serialized data block.

The accessor functions follow a rigid naming and signature convention. For
the `element` carrier:

```python
# mcdc/mcdc_get/element.py  (excerpt — ~322 lines in total)

import numba as nb
from numba import njit
import numpy as np

@njit
def xs_energy_grid(index, element, data):
    """Return the `index`-th energy grid point for `element`."""
    base = element["xs_energy_grid_offset"]
    return data["element_xs_energy_grid"][base + index]

@njit
def xs_energy_grid_all(element, data):
    """Return the full energy grid array for `element` (as a NumPy slice)."""
    base  = element["xs_energy_grid_offset"]
    n     = element["xs_energy_grid_size"]
    return data["element_xs_energy_grid"][base : base + n]

@njit
def total_xs(index, element, data):
    base = element["total_xs_offset"]
    return data["element_total_xs"][base + index]

@njit
def ionization_xs(index, element, data):
    base = element["ionization_xs_offset"]
    return data["element_ionization_xs"][base + index]

# ... repeated for elastic_xs, excitation_xs, bremsstrahlung_xs
# ... repeated for each reaction sub-table (delta distribution, mu CDF, etc.)
```

These files are called "auto-generated" because in principle a code
generation script could produce them from a schema definition. In
practice they are written by hand following the same pattern for each new
array.

**Registration**: In `mcdc/mcdc_get/__init__.py` import and re-export all
new accessor modules so the rest of the code can do:

```python
from mcdc_get import element as GET_ELEMENT
...
energy = GET_ELEMENT.xs_energy_grid(idx, elem, data)
```

---

## 9. Step 6 — Implement the Physics Module

**File**: `mcdc/transport/physics/<particle_type>/native.py`

This is the most substantial file. It contains all physical calculations
for your particle type. All functions must be decorated with
`@nb.njit(...)` and must only use Numba-compatible operations.

The module must expose exactly these four functions (the dispatcher
expects them by name):

```python
def particle_speed(particle_container)  → float
def macro_xs(reaction_type, particle_container, mcdc, data)  → float
def collision(particle_container, prog, data)  → float   # returns edep
# collision_distance is shared — you don't need to implement it
```

### 6.1 `particle_speed`

For non-relativistic particles (neutrons, protons above ~1 MeV rest
mass threshold):

```python
# Classical kinetic energy: E = ½mv²  →  v = sqrt(2E/m)
@njit
def particle_speed(particle_container):
    particle = particle_container[0]
    E = particle["E"]   # in eV
    # m in eV/c² (e.g., proton mass = 938.272e6 eV/c²)
    return LIGHT_SPEED * math.sqrt(2.0 * E / PROTON_MASS)
```

For **relativistic** particles (electrons, positrons, highly energetic
protons):

```python
# Relativistic: E_total = E_kinetic + m_e c²
#   p·c = sqrt(E_total² - (m_e c²)²)
#   β = pc / E_total
@njit
def particle_speed(particle_container):
    particle = particle_container[0]
    E = particle["E"]               # kinetic energy [eV]
    m = ELECTRON_MASS               # rest mass energy [eV]
    return LIGHT_SPEED * math.sqrt(E * (E + 2.0 * m)) / (E + m)
```

### 6.2 `macro_xs`

Iterates over all elements (or nuclides) in the current material and
sums density-weighted microscopic cross-sections:

```python
@njit
def macro_xs(reaction_type, particle_container, mcdc, data):
    particle  = particle_container[0]
    E         = particle["E"]
    material  = get_current_material(particle, mcdc, data)

    total = 0.0
    for i in range(material["num_elements"]):
        element_idx = material["element_indices"][i]
        element     = data["elements"][element_idx]
        density     = material["element_densities"][i]  # atoms/barn·cm

        # Linearly interpolate on energy grid
        xs = interpolate_xs(reaction_type, E, element, data)
        total += density * xs

    return total   # units: 1/cm
```

The helper `interpolate_xs` performs log-log or linear interpolation on
the tabulated data:

```python
@njit
def interpolate_xs(reaction_type, E, element, data):
    grid = GET_ELEMENT.xs_energy_grid_all(element, data)
    idx  = binary_search(grid, E)                     # lower bound index
    E0, E1 = grid[idx], grid[idx + 1]

    if reaction_type == REACTION_ELECTRON_IONIZATION:
        xs0 = GET_ELEMENT.ionization_xs(idx,     element, data)
        xs1 = GET_ELEMENT.ionization_xs(idx + 1, element, data)
    elif reaction_type == REACTION_ELECTRON_ELASTIC_SCATTERING:
        xs0 = GET_ELEMENT.elastic_xs(idx,     element, data)
        xs1 = GET_ELEMENT.elastic_xs(idx + 1, element, data)
    # ... etc.

    # Linear interpolation
    return xs0 + (xs1 - xs0) * (E - E0) / (E1 - E0)
```

### 6.3 `collision`

The main collision handler samples the reaction channel and dispatches to
the appropriate kernel:

```python
@njit
def collision(particle_container, prog, data):
    particle = particle_container[0]
    E        = particle["E"]

    # --- 1. Sample the colliding element ---
    material    = get_current_material(particle, ...)
    element_idx = sample_element(particle, material, data)
    element     = data["elements"][element_idx]

    # --- 2. Sample the reaction type ---
    xs_ion  = GET_ELEMENT.ionization_xs_at_E(E, element, data)
    xs_elas = GET_ELEMENT.elastic_xs_at_E(E, element, data)
    xs_exc  = GET_ELEMENT.excitation_xs_at_E(E, element, data)
    xs_brem = GET_ELEMENT.bremsstrahlung_xs_at_E(E, element, data)
    xs_tot  = xs_ion + xs_elas + xs_exc + xs_brem

    xi = rng() * xs_tot

    if xi < xs_ion:
        edep = ionization(particle_container, element, prog, data)
    elif xi < xs_ion + xs_elas:
        edep = elastic_scattering(particle_container, element, data)
    elif xi < xs_ion + xs_elas + xs_exc:
        edep = excitation(particle_container, element, data)
    else:
        edep = bremsstrahlung(particle_container, element, data)

    return edep
```

### 6.4 Individual Reaction Kernels

Each kernel modifies the particle in place (energy, direction) and
returns the local energy deposited (`edep`). Here are the patterns:

**Elastic scattering** — direction change, no energy loss:

```python
@njit
def elastic_scattering(particle_container, element, data):
    particle = particle_container[0]
    E        = particle["E"]

    # Sample scattering angle mu = cos(θ)
    xi = rng()
    if xi > LARGE_ANGLE_FRACTION:
        # Large angle: sample from tabulated CDF
        mu = sample_large_angle_mu(E, element, data)
    else:
        # Small angle: Coulomb screening approximation
        eta = compute_screening_parameter(E, element)
        mu  = sample_small_angle_mu_coulomb(eta)

    # Rotate direction
    rotate_direction(particle, mu, 2.0 * math.pi * rng())

    return 0.0   # no energy deposited in elastic scattering
```

**Excitation** — energy loss, no direction change, local deposition:

```python
@njit
def excitation(particle_container, element, data):
    particle = particle_container[0]
    E        = particle["E"]

    # Sample mean energy loss from stopping-power table
    eloss = evaluate_eloss(E, element, data)

    E_new = E - eloss
    if E_new < ELECTRON_CUTOFF_ENERGY:
        edep = E          # deposit all remaining energy
        particle["w"] = 0.0   # kill particle
    else:
        particle["E"] = E_new
        edep = eloss

    return edep
```

**Ionization** — energy loss + secondary particle creation:

```python
@njit
def ionization(particle_container, element, prog, data):
    particle = particle_container[0]
    E        = particle["E"]

    # Sample subshell
    rxn_idx  = sample_ionization_subshell(E, element, data)
    rxn      = data["ionization_reactions"][rxn_idx]
    E_b      = rxn["binding_energy"]   # binding energy of subshell

    # Sample secondary (delta) electron energy from tabulated distribution
    T_delta  = sample_delta_energy(E, rxn, data)
    T_prim   = E - E_b - T_delta       # primary electron kinetic energy after

    if T_prim < ELECTRON_CUTOFF_ENERGY:
        edep = E           # kill primary, deposit all
        particle["w"] = 0.0
        return edep

    # Sample directions from momentum conservation
    mu_prim  = sample_primary_mu(E, T_prim, T_delta)
    mu_delta = sample_delta_mu(E, T_prim, T_delta)

    # Update primary particle
    particle["E"] = T_prim
    rotate_direction(particle, mu_prim, 2.0 * math.pi * rng())

    # Create secondary (delta) electron
    if T_delta >= ELECTRON_CUTOFF_ENERGY:
        secondary = allocate_secondary(particle_container)
        secondary["E"]  = T_delta
        secondary["particle_type"] = PARTICLE_ELECTRON
        set_direction(secondary, mu_delta, particle, data)
        add_to_active_bank(secondary, prog)
    else:
        edep += T_delta    # below cutoff: deposit locally

    edep = E_b             # binding energy deposited in all cases
    return edep
```

**Bremsstrahlung** — electron loses energy; emitted photon not tracked
(in the current electron-only implementation):

```python
@njit
def bremsstrahlung(particle_container, element, data):
    particle = particle_container[0]
    E        = particle["E"]

    # Sample emitted photon energy from tabulated distribution
    E_photon = sample_photon_energy(E, element, data)
    E_new    = E - E_photon

    if E_new < ELECTRON_CUTOFF_ENERGY:
        edep = E
        particle["w"] = 0.0
        return edep

    particle["E"] = E_new
    # Photon is not tracked — its energy is NOT deposited locally either
    # (it escapes to be tallied elsewhere if photon transport is enabled)
    return 0.0
```

---

## 10. Step 7 — Wire into the Physics Dispatcher

**File**: `mcdc/transport/physics/interface.py`

This is the **only** file that imports from multiple particle physics
sub-packages. It contains `if/elif` chains on `particle_type`. Adding
your particle means adding one `elif` branch to each dispatcher function:

```python
# mcdc/transport/physics/interface.py

from mcdc.transport.physics.neutron  import native as neutron
from mcdc.transport.physics.electron import native as electron
# from mcdc.transport.physics.proton  import native as proton  ← add this

@njit
def particle_speed(particle_container):
    ptype = particle_container[0]["particle_type"]
    if ptype == PARTICLE_NEUTRON:
        return neutron.particle_speed(particle_container)
    elif ptype == PARTICLE_ELECTRON:
        return electron.particle_speed(particle_container)
    # elif ptype == PARTICLE_PROTON:
    #     return proton.particle_speed(particle_container)

@njit
def macro_xs(reaction_type, particle_container, mcdc, data):
    ptype = particle_container[0]["particle_type"]
    if ptype == PARTICLE_NEUTRON:
        return neutron.macro_xs(reaction_type, particle_container, mcdc, data)
    elif ptype == PARTICLE_ELECTRON:
        return electron.macro_xs(reaction_type, particle_container, mcdc, data)

@njit
def collision_distance(particle_container, mcdc, data):
    # SHARED — exponential sampling, particle-type-agnostic
    sigma_t = macro_xs(REACTION_TOTAL, particle_container, mcdc, data)
    return -math.log(rng(particle_container)) / sigma_t

@njit
def collision(particle_container, prog, data):
    ptype = particle_container[0]["particle_type"]
    if ptype == PARTICLE_NEUTRON:
        return neutron.collision(particle_container, prog, data)
    elif ptype == PARTICLE_ELECTRON:
        return electron.collision(particle_container, prog, data)
```

Note that `collision_distance` is **shared** — it just calls `macro_xs`
with the total cross-section. You do not need to re-implement it for each
particle type.

---

## 11. Step 8 — Extend the Source Definition

**File**: `mcdc/object_/source.py`

Users specify the particle type when defining a source:

```python
# mcdc/object_/source.py  (simplified excerpt)

class Source:
    def __init__(self,
                 energy: np.ndarray = None,
                 position = None,
                 direction = None,
                 particle_type: str | int = "neutron",  # ← changed to accept str
                 ...):

        # Convert string → integer constant
        if isinstance(particle_type, str):
            mapping = {
                "neutron":  PARTICLE_NEUTRON,
                "electron": PARTICLE_ELECTRON,
                # "proton":   PARTICLE_PROTON,  ← add here
            }
            self.particle_type = mapping[particle_type.lower()]
        else:
            self.particle_type = particle_type
```

When a particle is sampled from the source bank, the `particle_type`
field is copied into the new `ParticleData` struct. No further changes to
the source sampling logic are needed — the discriminator field travels
with the particle from birth through its entire history.

### Usage in an input file

```python
# test/regression/electron_tests/lockwood/slab_Al.py  (excerpt)

mcdc.source(
    z=[z0 + TINY, z0 + TINY],     # point source on the left face
    particle_type="electron",
    energy=np.array([[1e6 - 1, 1e6 + 1],   # energy distribution:
                     [0.5,     0.5    ]]),  # uniform between 999999 and 1000001 eV
    direction=[math.sin(theta), TINY, math.cos(theta)]
)
```

---

## 12. Step 9 — Add New Tally Scores if Needed

**File**: `mcdc/constant.py` and `mcdc/transport/tally/score.py`

For electrons, energy deposition (`edep`) was added as a new score type:

```python
# mcdc/constant.py
SCORE_FLUX = 0
SCORE_CURRENT = 1
# ...
SCORE_EDEP = 13     # ← new for electron energy deposition
```

In `score.py`, add a branch to the scoring function:

```python
# mcdc/transport/tally/score.py  (simplified)

@njit
def score_tally(score_type, edep, particle, tally, data):
    if score_type == SCORE_FLUX:
        score_flux(particle, tally, data)
    elif score_type == SCORE_CURRENT:
        score_current(particle, tally, data)
    elif score_type == SCORE_EDEP:
        score_edep(edep, particle, tally, data)   # ← new branch

@njit
def score_edep(edep, particle, tally, data):
    # Find the tally bin(s) this particle falls into
    idx = get_tally_index(particle, tally, data)
    if idx >= 0:
        tally["edep"][idx] += edep * particle["w"]
```

The `edep` value comes from the return value of `physics.collision()`,
which propagates back through the simulation loop in
`transport/simulation.py`:

```python
# transport/simulation.py  (step_particle, simplified)

if particle["event"] & EVENT_COLLISION:
    edep = physics.collision(particle_container, prog, data)
    tally.score_tally(SCORE_EDEP, edep, particle, ...)
```

---

## 13. Step 10 — Write Regression Tests

**Directory**: `test/regression/<particle>_tests/`

The electron implementation includes two Lockwood validation tests.
A minimal regression test structure looks like this:

```python
# test/regression/electron_tests/lockwood/slab_Al.py

import mcdc
import numpy as np
import math

# --- Physical setup ---
CSDA_RANGE  = 0.569   # g/cm²  (Continuous Slowing Down Approximation range)
DENSITY     = 2.70    # g/cm³  aluminum
THICKNESS   = CSDA_RANGE / DENSITY  # cm

# --- Geometry ---
z0, z5 = 0.0, THICKNESS
TINY   = 1e-10  # avoid surface-exactly placement

surface_left  = mcdc.surface("plane-z", z=z0, bc="vacuum")
surface_right = mcdc.surface("plane-z", z=z5, bc="vacuum")

mat_Al = mcdc.Material(
    element_composition={"Al": 6.026e22 * 1e-24}  # atoms/barn·cm
)

cell = mcdc.cell([+surface_left, -surface_right], mat_Al)

# --- Source: 1 MeV parallel electron beam ---
theta = 0.0
mcdc.source(
    z=[z0 + TINY, z0 + TINY],
    particle_type="electron",
    energy=np.array([[1e6 - 1, 1e6 + 1], [0.5, 0.5]]),
    direction=[math.sin(theta), TINY, math.cos(theta)]
)

# --- Tally ---
N_BINS = 40
z_bins = np.linspace(z0, z5, N_BINS + 1)
mcdc.tally.mesh_tally(scores=["edep", "flux"], z=z_bins)

# --- Settings ---
mcdc.setting(N_particle=100, active_bank_buff=10000)
mcdc.run()
```

Good tests for a new particle type should include:
- A simple analytic case where the correct answer is known (e.g., monoenergetic beam in infinite homogeneous medium).
- A comparison against a reference code (MCNP6, EGSnrc, Geant4) for a realistic geometry.
- A test of secondary particle creation and scoring.
- A test that verifies cutoff-energy behavior (particles dying below threshold).

---

## 14. Key Design Patterns and Conventions

### 14.1 Numba Compatibility Rules

- Use `@nb.njit` on all hot-path functions.
- Data structures must be NumPy structured arrays, not Python objects.
- No `if isinstance(...)` or dynamic dispatch inside JIT functions.
- Constants must be module-level Python scalars (not `numpy.float64`).
- Use `math.sqrt`, `math.log`, `math.pi` — **not** `numpy.sqrt` etc.
  inside `@njit` functions.
- Binary search on sorted arrays: implement manually or use
  `np.searchsorted` (which Numba supports).

### 14.2 Random Number Generation

Every stochastic sample must consume exactly one random number and
advance the per-particle RNG seed:

```python
# Canonical pattern for sampling:
xi = rng(particle_container)   # draws U(0,1), advances particle["rng_seed"]
mu = 2.0 * xi - 1.0           # cosine uniformly in [-1, 1]
```

Never use `numpy.random` or Python's `random` module inside JIT code.

### 14.3 Reaction Return Values

- Elastic scattering / direction-only changes: return `0.0` (no local
  energy deposition).
- Absorptive reactions: return the particle's full energy.
- Partially inelastic: return the energy transferred to the medium.
- Secondary creation: secondary particle's energy is **not** included in
  `edep` (it will be deposited later when the secondary is tracked).

### 14.4 Cutoff Energy

Every particle type needs a minimum energy threshold below which tracking
stops. Below cutoff, the particle's remaining kinetic energy is deposited
locally and the particle is killed by setting `particle["w"] = 0.0`.

```python
if E_new < ELECTRON_CUTOFF_ENERGY:
    edep = E              # deposit ALL remaining kinetic energy
    particle["w"] = 0.0   # mark for termination
    return edep
```

### 14.5 Secondary Particle Direction

When a secondary is created, its direction must be set in the **lab
frame**, not the center-of-mass frame. The helper function
`rotate_direction(particle, mu, phi)` rotates the current direction
vector by polar angle `arccos(mu)` and azimuthal angle `phi`.

For secondary particles created in ionization, the direction relative to
the primary is computed from momentum conservation and then rotated from
the primary's reference frame to the lab frame.

---

## 15. Physics Concepts You Must Understand Before Starting

Before implementing a new particle, you need to understand:

### 15.1 Relativistic vs. Non-relativistic Kinematics

Electrons at 1 MeV travel at ~94% the speed of light. Their speed must
be computed relativistically. Protons become relativistic only above ~100
MeV. The speed formula matters because it determines:
- The particle's velocity for time-of-flight calculations.
- Direction sampling after collisions (relativistic aberration).

### 15.2 Continuous vs. Discrete Energy Loss

Neutrons lose energy only in discrete scattering/reaction events. Electrons
lose energy continuously as they travel through matter (electronic stopping
power / Bethe-Bloch formula), but MC/DC implements this as discrete collision
events by sampling from interaction cross-sections directly. This is valid
when the cross-sections are fine enough (i.e., tabulated at sufficient energy
resolution).

If you add protons, you face the same choice: continuous-slowing-down
approximation (CSDA) vs. explicit discrete collisions.

### 15.3 Cross-Section Data Format

Different particle types use different data library formats:
- **Neutrons**: ENDF/B (evaluated nuclear data), processed into ACE format.
- **Electrons/Positrons**: EEDL (Evaluated Electron Data Library) or
  eprdata14 (LANL), stored as HDF5 in MC/DC's library format.
- **Photons**: EPDL (Evaluated Photon Data Library).
- **Protons**: TENDL or IAEA proton libraries.

You must either find a pre-existing HDF5 converter for your data library
or write one.

### 15.4 Angular Distributions

Many reactions have anisotropic angular distributions:
- Coulomb scattering is strongly forward-peaked — it requires special
  treatment (screening parameter, split between large-angle and small-angle
  regimes).
- Isotropic distributions are the simple case (`mu = 2ξ − 1`).
- Tabulated distributions require interpolation in both energy and angle.

### 15.5 Secondary Particle Production

For ionization, two outgoing particles exist (primary + delta electron).
For bremsstrahlung, the photon may or may not be tracked depending on
whether photon transport is enabled. Design your collision kernel to
handle both cases cleanly, returning the correct `edep` in each scenario.

---

## 16. Reference: Electron vs. Neutron Comparison Table

| Aspect | Neutron | Electron |
|--------|---------|----------|
| Type constant | `PARTICLE_NEUTRON = 0` | `PARTICLE_ELECTRON = 1` |
| Physics carrier | `Nuclide` (ENDF data) | `Element` (EEDL data) |
| Material composition key | `nuclide_composition` | `element_composition` |
| Speed formula | Classical: `sqrt(2E/m)` | Relativistic: `c·sqrt(E(E+2m))/(E+m)` |
| Reactions | Elastic, capture, inelastic, fission | Elastic, ionization, excitation, bremsstrahlung |
| Energy loss mode | Discrete (only at collisions) | Discrete (tabulated per-event) |
| Secondary particles | Prompt neutrons, delayed neutrons | Delta electrons (tracked); photons (untracked) |
| Cutoff energy | ~1×10⁻⁵ eV (thermal floor) | 100 eV (`ELECTRON_CUTOFF_ENERGY`) |
| Cross-section data | ENDF/ACE format | EEDL/HDF5 format |
| `collision()` return value | `None` (no edep scoring) | `float` (energy deposited) |
| Key new constant | `AVOGADRO_NUMBER`, `NEUTRON_MASS` | `ELECTRON_MASS`, `FINE_STRUCTURE_CONSTANT` |
| Tally scores | flux, current, fission rate | flux, current, `edep` |

---

## 17. Common Pitfalls

1. **Forgetting to export from `__init__.py`**: Both `mcdc_get/__init__.py`
   and `mcdc_set/__init__.py` must explicitly import and register your new
   accessor modules. Missing this causes silent failures where Numba cannot
   find the function.

2. **Using Python objects inside `@njit`**: The most common Numba error.
   If you store `Element` or `Reaction` Python objects and try to access them
   inside a JIT function, Numba will refuse to compile. All data must be
   pre-serialized into NumPy structured arrays.

3. **Off-by-one in energy grid interpolation**: `binary_search` returns the
   lower index. Make sure you do not access `grid[idx + 1]` when `idx` is
   already the last index. Add a guard or ensure the particle energy is
   always within `[E_min, E_max]` before interpolating.

4. **Not killing particles below cutoff**: If you forget to set
   `particle["w"] = 0.0` when `E < cutoff`, the simulation loop will
   continue transporting zero-energy particles indefinitely, causing an
   infinite loop or nonsensical results.

5. **Energy conservation errors in secondary creation**: The sum of
   (primary energy after) + (secondary energy) + (edep) must equal
   (primary energy before). Verify this invariant in unit tests.

6. **Wrong frame for secondary directions**: Direction angles from reaction
   kinematics are usually in the projectile's rest frame or center-of-mass
   frame. They must be rotated to the lab frame before storing in the
   particle struct.

7. **HDF5 file path issues**: The library path is read from `$MCDC_LIB`.
   If this environment variable is not set or points to the wrong directory,
   `Element.__init__` will silently fail to load data. Add an informative
   error message.

8. **Mutually exclusive material compositions**: The current code does not
   support a material that is simultaneously defined by nuclides (for
   neutrons) and elements (for electrons). If you need multi-particle
   transport through the same geometry, you will need to extend the
   `Material` class to allow both composition types simultaneously.

---

## 18. Nuclear Data and Cross-Section Libraries

### Electron data (eprdata14 / EEDL)

The electron implementation uses LANL's `eprdata14` library, derived from
the EEDL (Evaluated Electron Data Library):

- **Source**: `LA-UR-14-24544` (Cullen et al.)
- **Download**: Available through NNDC or LANL's T-2 nuclear information
  service.
- **HDF5 converter**: A pre-processing script converts the raw EEDL ASCII
  files into the HDF5 format that MC/DC expects. This script is not
  included in the repository but must be run once to build the library
  before running electron simulations.
- **Environment variable**: Set `MCDC_LIB=/path/to/electron/hdf5/library`
  before running.

### Neutron data (ENDF/B)

For reference, neutron cross-sections come from ENDF/B-VIII.0 or later,
processed through NJOY into MC/DC's internal HDF5 format.

### Validation dataset

The Lockwood calorimetric measurements (`Lockwood et al., 1987`) provide
experimental benchmarks for electron energy deposition in aluminum slabs.
MCNP6.3 comparisons are documented in `LA-UR-23-32743` (Kulesza et al.).
Both are referenced in `MCDC/test/regression/electron_tests/lockwood/references.md`.

---

*End of document. For questions or corrections, open an issue in the
repository or contact the MC/DC development team.*