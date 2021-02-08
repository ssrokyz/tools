#!/usr/bin/env python
import numpy as np

# 
prim_cell  = 'Si-diamond-prim.vasp'
N          = 5
NNN        = ((N,0,0),(0,N,0),(0,0,N))
T          = 300 #K
seed_range = range(0,30,1)
calc       = 'lmp'
cp_files   = ('frozen_model.pb',)

def get_phonon_distrib_alist(
    prim_cell,
    NNN,
    T,
    seed_range,
    calc,
    cp_files=None
    ):
    """
    prim_cell (str)
        ASE readable primitive unitcell structure file.
    NNN (list of int, shape: (3,3))
        Supercell matrix used to calculate force constants.
    T (float)
        Temperature in Kelvin unit.
    seed_range (range or list of int)
        Seeds for random number generation.
    calc (str, choices: ('lmp', 'vasp'))
        Calculator for force calculation.
    cp_files (list of str)
        List of input files for force calculation.
    """

    # Main
    from ase.io import read, write
    atoms = read(prim_cell)
    from phonopy import Phonopy
    phonon = Phonopy(
        atoms,
        NNN,
        )
    phonon.generate_displacements(
        0.03,
        )
    pho_super = phonon.get_supercell()
    pho_disp  = phonon.get_supercells_with_displacements()
    from phonopy.interface import vasp
    vasp.write_supercells_with_displacements(
        pho_super,
        pho_disp,
        )
    import ss_phonopy as ssp
    phonon = ssp.calc_phonon(
        calc,
        phonon,
        cp_files=cp_files,
        )
    masses = pho_super.masses
    fc = np.reshape(
        np.transpose(
            phonon.get_force_constants(),
            axes=(0,2,1,3),
            ),
        (3*len(masses), 3*len(masses)),
        )
    # Build dynamical matrix
    rminv = (masses ** -0.5).repeat(3)
    dynamical_matrix = fc * rminv[:, None] * rminv[None, :]
    # Solve eigenvalue problem to compute phonon spectrum and eigenvectors
    eigen_set = np.linalg.eigh(dynamical_matrix)

    from ase.md.velocitydistribution import phonon_harmonics
    from ase import Atoms, units
    alist = []
    for i in seed_range:
        d_ac, v_ac = phonon_harmonics(
            None,
            masses,
            T *units.kB,
            eigen_set=eigen_set,
            # rng=np.random.rand,
            seed=i,
            quantum=True,
            # plus_minus=True,
            # return_eigensolution=False,
            # failfast=True,
            )
        new_super = Atoms(
            cell       = pho_super.get_cell(),
            symbols    = pho_super.get_chemical_symbols(),
            positions  = pho_super.get_positions() + d_ac,
            velocities = v_ac,
            pbc        = True,
            )
        alist.append(new_super)
    return(alist)
