#! /Library/Frameworks/Python.framework/Versions/3.7/bin/python3
# ============================================== #
# ============= A: Coarse Grainer =============  #
# ============================================== #
# Written by Forrest Bicker
# August 2019
#

# O(fr)
# f = number of frames
# r = number of residue segments

# ================= Requiremet ================= #
# from collections import defaultdict
import os
# import math

import MDAnalysis as mda
from util import progress

from json import load


# ================ Input Files ================  #
topology = 'inputs/alanin.pdb'
trajectory = 'inputs/alanin.dcd'
simulation_name = 'alanin'
simulation_name = os.path.basename(topology).split(".")[0]

# ================= User Input ================= #
residue_list = ['ALA']  # list of ammino acids to be CoarseGrained
# residue_list = ['DA', 'DT', 'DG', 'DC', 'PHOSPHATE', 'RIBOSE']

# ============== Misc Initiation ==============  #
with open('mapping_dict.json', "r") as f:
    mapping_dict = load(f)

with open('abrev_dict.json', "r") as f:
    abrev_dict = load(f)


# ================= Execution =================  #
print('Generating Universe...')
if trajectory != "":
    u = mda.Universe(topology, trajectory)
else:
    u = mda.Universe(topology)
print('Universe Generated!')

print('Genarating Coarse Gained Molecules...')

print(u.bonds)
print('Calculating Bond connections...')
resnames = ' '.join(residue_list)
u.select_atoms(f'resname {resnames}').guess_bonds(vdwradii={'MN': 1})
print(u.bonds)

bead_data = []
cg_beads = []
for resname in residue_list:  # loops tru each residue to be coarse grained
    if resname == "PHOSPHATE" or resname == "RIBOSE":
        resname_atoms = u.atoms.select_atoms('resname DA DT DG DC DU')
    else:
        resname_atoms = u.atoms.select_atoms(f'resname {resname}')  # selects all resname-specific atoms
    residues = resname_atoms.residues  # identifys all resname-specific residues
    for residue in residues:  # loops thu each matching residue id
        resid = residue.resid  # store int id
        try:
            segments = mapping_dict[resname].keys()
            for segment in segments:  # loops thru each segment of each residue
                params = 'name ' + ' '.join(mapping_dict[resname][segment])  # generates param
                # selects all atoms in a given residue segment
                atms = residue.atoms.select_atoms(params)
                dummy = atms[0]
                # names dummy atom in propper format
                dummy.name = str(abrev_dict[resname]) + str(segment[0]) + str(resid)
                dummy.type = str(segment[0])

                bead_data.append((dummy, atms))
                cg_beads.append(dummy)

                for atm in atms:
                    atm.type = dummy
        except KeyError:
            print(f'{resname} was not found in abrev_dict, skipping coarse grain. Please add its parameters to the dictionary. (See README section A3. for help)')

cg_beads = mda.AtomGroup(cg_beads)

new_bonds = []
for dummy, atms in bead_data:
    for bond in dummy.bonds:
        for atom in bond.atoms:
            if atom != dummy:
                if atom not in atms:
                    try:
                        new_bonds.append([dummy.ix, atom.type.ix]) # type is used to store the cluster dummy
                    except AttributeError: # raises if connected atom is annother dummy
                        new_bonds.append([dummy.ix, atom.ix])
for bond in u.bonds:
    u.delete_bonds([bond])

u.add_TopologyAttr('bonds', new_bonds)

print('Writing Output Files...')

if trajectory != "":
    number_of_frames = len(u.trajectory)
    progress(0)
    with mda.Writer(f'outputs/CoarseGrain/{simulation_name}_CG.dcd', cg_beads.n_atoms, multiframe=True, bonds='all') as w:
        for frame in u.trajectory:  # loops tru each frame
            f = frame.frame

            # positions a dummy atoms at cluster center of mass
            for dummy, atms in bead_data:
                dummy.position = atms.center_of_mass()

            w.write(cg_beads)
            progress(f / number_of_frames)
    progress(1)

    print('\nGenerated All Coarse Grained Molecules!')
    print(f'Trajectory written to {simulation_name}_CG.dcd!')
else:
    for dummy, atms in bead_data:
        dummy.position = atms.center_of_mass()

for dummy, atms in bead_data:
        dummy.type = ''

cg_beads.write(f'outputs/CoarseGrain/{simulation_name}_CG.pdb', bonds='all')
print(f'Topology written to {simulation_name}_CG.pdb!')
print(f'Reduced {len(u.atoms)} atoms to {len(cg_beads)} beads!')

print('Task complete!')
