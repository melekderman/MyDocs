"""
ACEtk EPRDATA14 Structure Inspector
Loads the first element (H) and prints the full structure of every block.
Run this to verify ACEtk API and data availability before running the generator.

Usage:
    python inspect_acetk.py
"""

import ACEtk
import numpy as np
import os

# =============================================================================
# Configuration
# =============================================================================
ACE_FILE = os.getenv("MCDC_ACELIB_ELECTRON")
if ACE_FILE is None:
    raise EnvironmentError("$MCDC_ACELIB_ELECTRON is not set")

ELEMENT = "1000.14p"  # Change to inspect a different element

# =============================================================================

def section(title):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")

def subsection(title):
    print(f"\n  --- {title} ---")

def show(label, value):
    print(f"    {label}: {value}")

def show_array(label, arr):
    arr = np.array(arr)
    print(f"    {label}: shape={arr.shape}, min={arr.min():.4e}, max={arr.max():.4e}")

# =============================================================================
# Load table
# =============================================================================
section("Loading EPRDATA14")
print(f"  ACE file : {ACE_FILE}")
print(f"  Element  : {ELEMENT}")

all_tables = ACEtk.PhotoatomicTable.from_concatenated_file(ACE_FILE)
table_map  = {t.zaid: t for t in all_tables}

print(f"  Total tables loaded: {len(table_map)}")
assert ELEMENT in table_map, f"ZAID {ELEMENT} not found in file"

table = table_map[ELEMENT]

# =============================================================================
# Header
# =============================================================================
section("Header")
header = table.header
show("zaid",               table.zaid)
show("title",              header.title)
show("date",               header.date)
show("atomic_weight_ratio",table.atomic_weight_ratio)
show("atom_number (Z)",    table.atom_number)

# =============================================================================
# Electron cross section block (ESZG)
# =============================================================================
section("Electron Cross Section Block (ESZG)")
xs0 = table.electron_cross_section_block
show("number_energy_points",     xs0.number_energy_points)
show_array("energies (MeV)",     xs0.energies)
show_array("elastic",            xs0.elastic)
show_array("bremsstrahlung",     xs0.bremsstrahlung)
show_array("excitation",         xs0.excitation)
show_array("total",              xs0.total)

subsection("Electroionization xs per subshell")
N_subshells = xs0.number_electron_subshells
show("number_electron_subshells", N_subshells)
for i in range(N_subshells):
    show_array(f"electroionisation({i+1})", xs0.electroionisation(i + 1))

# =============================================================================
# Electron subshell block (SUBSH)
# =============================================================================
section("Electron Subshell Block (SUBSH)")
subsh = table.electron_subshell_block
show("number_electron_subshells", subsh.number_electron_subshells)
show("designators",               list(subsh.designators))
show("binding_energies (MeV)",    list(subsh.binding_energies))
show("populations",               list(subsh.populations))
show("number_transitions",        list(subsh.number_transitions))

# =============================================================================
# Elastic angular distribution block (ELAS)
# =============================================================================
section("Elastic Angular Distribution Block (ELAS)")
ang = table.electron_elastic_angular_distribution_block
show("number_energy_points", ang.number_energy_points)
show_array("energies (MeV)", ang.energies)

subsection("First distribution")
dist = ang.distributions[0]
show("energy (MeV)",   dist.energy)
show("number_cosines", dist.number_cosines)
show_array("cosines",  dist.cosines)
show_array("cdf",      dist.cdf)

subsection("Last distribution")
dist = ang.distributions[-1]
show("energy (MeV)",   dist.energy)
show("number_cosines", dist.number_cosines)

# =============================================================================
# Excitation energy loss block (EXCIT)
# =============================================================================
section("Excitation Energy Loss Block (EXCIT)")
excit = table.electron_excitation_energy_loss_block
show("number_energy_points",        excit.number_energy_points)
show_array("energies (MeV)",        excit.energies)
show_array("excitation_energy_loss", excit.excitation_energy_loss)

# =============================================================================
# Bremsstrahlung energy distribution block (BREME)
# =============================================================================
section("Bremsstrahlung Energy Distribution Block (BREME)")
brems = table.bremsstrahlung_energy_distribution_block
show("number_energy_points", brems.number_energy_points)
show_array("energies (MeV)", brems.energies)

subsection("First distribution")
dist = brems.distributions[0]
show("energy (MeV)",            dist.energy)
show("number_outgoing_energies", dist.number_outgoing_energies)
show_array("outgoing_energies", dist.outgoing_energies)
show_array("cdf",               dist.cdf)

subsection("Last distribution")
dist = brems.distributions[-1]
show("energy (MeV)",            dist.energy)
show("number_outgoing_energies", dist.number_outgoing_energies)

# =============================================================================
# Electroionization energy distribution block (EION) — per subshell
# =============================================================================
section("Electroionization Energy Distribution Block (EION)")
for i in range(N_subshells):
    subsection(f"Subshell {i+1} (designator={list(subsh.designators)[i]})")
    eion = table.electroionisation_energy_distribution_block(i + 1)
    show("number_energy_points", eion.number_energy_points)
    show_array("energies (MeV)", eion.energies)

    dist = eion.distributions[0]
    show("first dist energy (MeV)",        dist.energy)
    show("number_outgoing_energies",        dist.number_outgoing_energies)
    show_array("outgoing_energies (MeV)",   dist.outgoing_energies)
    show_array("cdf",                       dist.cdf)

# =============================================================================
# Subshell transition data block (atomic relaxation)
# =============================================================================
section("Subshell Transition Data Block (Atomic Relaxation)")
relax = table.subshell_transition_data_block
show("number_electron_subshells", relax.number_electron_subshells)

for i in range(N_subshells):
    td = relax.transition_data(i + 1)
    subsection(f"Subshell {i+1} — number_transitions={td.number_transitions}")
    if td.number_transitions > 0:
        for j in range(td.number_transitions):
            jdx = j + 1
            print(f"      transition {jdx}: "
                  f"primary={td.primary_designator(jdx)}, "
                  f"secondary={td.secondary_designator(jdx)}, "
                  f"energy={td.energy(jdx):.4e} MeV, "
                  f"probability={td.probability(jdx):.4e}")

# =============================================================================
# Summary
# =============================================================================
section("Summary")
show("Element",         f"Z={table.atom_number}")
show("Energy points",   xs0.number_energy_points)
show("Subshells",       N_subshells)
show("Elastic energies",ang.number_energy_points)
show("Brems energies",  brems.number_energy_points)
show("Excit energies",  excit.number_energy_points)
print()
