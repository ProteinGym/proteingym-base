# Chapter 3: Creating and Using a Structure Dataset

## Introduction

The structure dataset component of the PG2 dataset system allows you to work with molecular structure data from various file formats including PDB, mmCIF, and binary CIF. This chapter explains how to create, load, and use structure datasets in your projects.

## Understanding the StructureDataset

The `StructureDataset` class is designed to handle structural data of biological molecules with flexibility in the backend library used. It provides functionality for:

1. Loading structure data from various file formats (PDB, mmCIF, binary CIF)
2. Supporting multiple backend libraries (Biopython and Biotite)
3. Handling both single structure files and directories of structures
4. Providing a consistent interface regardless of the backend used

## Backend Libraries

The `StructureDataset` supports two popular Python libraries for structural bioinformatics:

1. **Biopython**: A widely used library with comprehensive tools for computational molecular biology
2. **Biotite**: A modern, object-oriented library for the analysis and processing of biological data

The system automatically selects an appropriate backend based on what's installed in your environment, with Biopython being the first choice if both are available.

## Creating a Structure Dataset

There are two main ways to create a structure dataset:

### 1. From a dataset.toml File

The most common approach is to create a structure dataset through a `dataset.toml` file:

```python
from pg2_dataset.dataset import Dataset

# Load the dataset from a TOML file
dataset = Dataset.from_toml("path/to/dataset.toml")

# Access the structure dataset
structure_dataset = dataset.structure
```

For this to work, your dataset.toml file must include a structure resource:

```toml
[resources]
records = "path/to/records.csv"
structure = "path/to/structure.pdb"  # Can be .pdb, .cif, or .bcif
```

### 2. Directly Creating a StructureDataset

You can also create a `StructureDataset` directly:

```python
from pg2_dataset.backends import StructureDataset

# Create the dataset with a file path to a single structure
structure_dataset = StructureDataset(file_path="path/to/structure.pdb")

# Or with a directory containing multiple structures
structure_dataset = StructureDataset(file_path="path/to/structures_directory/")
```

## Supported File Formats

The `StructureDataset` supports the following file formats:

1. **PDB** (.pdb): The classic Protein Data Bank format
2. **mmCIF** (.cif): The macromolecular Crystallographic Information File format
3. **Binary CIF** (.bcif): A binary version of the CIF format

The appropriate parser is selected automatically based on the file extension.

## Structure Managers

The `StructureDataset` uses a dependency injection pattern with `StructureManager` implementations:

1. `BiopythonStructureManager`: Uses Biopython's parsers
2. `BiotiteStructureManager`: Uses Biotite's parsers

The appropriate manager is selected automatically based on available libraries in your environment.

## Accessing Structure Data

Once you've loaded a structure dataset, you can access the structures:

```python
# Access all loaded structures
structures = structure_dataset.structures

# Access a specific structure by its ID (usually the filename)
structure_id = next(iter(structures.keys()))
structure = structures[structure_id]
```

### Working with Biopython Structures

If using the Biopython backend:

```python
# Assuming Biopython is being used
structure = next(iter(structure_dataset.structures.values()))

# Access model, chain, residue, and atom data
model = structure[0]  # First model
for chain in model:
    print(f"Chain ID: {chain.id}")
    for residue in chain:
        print(f"  Residue: {residue.resname} {residue.id[1]}")
        for atom in residue:
            print(f"    Atom: {atom.name}, Coordinates: {atom.coord}")
```

### Working with Biotite Structures

If using the Biotite backend:

```python
# Assuming Biotite is being used
atom_array = next(iter(structure_dataset.structures.values()))

# Access atom data
print(f"Number of atoms: {len(atom_array)}")
print(f"Chain IDs: {atom_array.chain_id}")
print(f"Residue names: {atom_array.res_name}")
print(f"Atom coordinates: {atom_array.coord}")
```

## Loading Multiple Structures

The `StructureDataset` can load multiple structures from a directory:

```python
# Load all structures from a directory
structure_dataset = StructureDataset(file_path="path/to/structures_directory/")

# Access the loaded structures
print(f"Loaded {len(structure_dataset.structures)} structures")
for structure_id, structure in structure_dataset.structures.items():
    print(f"Structure ID: {structure_id}")
```

## Installation Requirements

To use the `StructureDataset`, you need to install either Biopython or Biotite:

```bash
# Install with Biopython
pip install biopython

# Or install with Biotite
pip install biotite

# Or install both
pip install biopython biotite

# Or use the project's extras
uv sync --all-extras
```

If neither library is installed and you try to load a structure, an `ImportError` will be raised with instructions.

## Example Usage

Here's a complete example of working with a structure dataset:

```python
from pg2_dataset.dataset import Dataset
from pg2_dataset.backends import StructureDataset

# Method 1: Load from dataset.toml
dataset = Dataset.from_toml("example_data/dataset.toml")
structure_dataset = dataset.structure

# Method 2: Create directly
# structure_dataset = StructureDataset(file_path="path/to/structure.pdb")

# Check which structures are loaded
print(f"Loaded structures: {list(structure_dataset.structures.keys())}")

# Process the first structure
structure_id = next(iter(structure_dataset.structures.keys()))
structure = structure_dataset.structures[structure_id]

# The rest depends on which backend is being used (Biopython or Biotite)
# For Biopython:
try:
    # Check if it's a Biopython structure
    model = structure[0]
    print(f"Using Biopython backend")
    print(f"Structure ID: {structure_id}")
    print(f"Number of chains: {len(model)}")
    
    # Count residues and atoms
    residue_count = sum(1 for _ in model.get_residues())
    atom_count = sum(1 for _ in model.get_atoms())
    print(f"Number of residues: {residue_count}")
    print(f"Number of atoms: {atom_count}")
    
except (TypeError, AttributeError):
    # It's probably a Biotite structure
    print(f"Using Biotite backend")
    print(f"Structure ID: {structure_id}")
    print(f"Number of atoms: {len(structure)}")
    
    # If it's an atom array
    if hasattr(structure, "coord"):
        print(f"Coordinate shape: {structure.coord.shape}")
```

## Best Practices

1. **Backend Consistency**: For consistency in your code, consider standardizing on either Biopython or Biotite
2. **Error Handling**: Add try-except blocks when working with structures to handle potential format issues
3. **File Organization**: When working with multiple structures, use a consistent naming convention
4. **Path Configuration**: Use absolute paths or ensure relative paths are correct
5. **Memory Management**: Be aware that large structures can consume significant memory

## Troubleshooting

Common issues when working with structure datasets:

1. **Missing Dependencies**: Ensure either Biopython or Biotite is installed
2. **File Not Found**: Verify that the path to your structure file is correct
3. **Unsupported Format**: Check that your file has one of the supported extensions (.pdb, .cif, .bcif)
4. **Backend-Specific Code**: Be aware that code written for one backend may not work with the other
5. **Memory Issues**: Large structures may cause memory problems; consider processing data in chunks

## Summary

The structure dataset provides a flexible way to work with molecular structure data in the PG2 dataset system. By supporting multiple backends (Biopython and Biotite) and file formats (PDB, mmCIF, binary CIF), it allows you to choose the tools that best fit your needs. The dependency injection pattern ensures that your code can work with either backend, providing flexibility and future-proofing your analysis pipelines.