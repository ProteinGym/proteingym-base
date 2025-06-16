# Chapter 4: Creating and Using a MSA Dataset

## Introduction

Multiple Sequence Alignments (MSAs) are essential tools in bioinformatics for comparing and analyzing related protein or nucleic acid sequences. The `MSADataset` class in the PG2 dataset system provides functionality for working with MSA data in various formats. This chapter explains how to create, load, and use MSA datasets in your projects.

## Understanding the MSADataset

The `MSADataset` class is designed to handle multiple sequence alignment data from various file formats. It provides functionality for:

1. Loading MSA data from different file formats (A2M, A3M, PSI)
2. Parsing and organizing sequence records
3. Accessing aligned sequences
4. Extracting record names from different header formats

## Supported MSA Formats

The `MSADataset` supports three common MSA file formats:

1. **A2M**: Aligned FASTA format where gaps in the query sequence are represented by dashes (-) and gaps in the target sequences are represented by lowercase letters
2. **A3M**: Similar to A2M but with lowercase letters in the target sequences removed
3. **PSI**: A simple format where each line contains a header and a sequence separated by whitespace

## Creating an MSA Dataset

There are two main ways to create an MSA dataset:

### 1. From a dataset.toml File

The most common approach is to create an MSA dataset through a `dataset.toml` file:

```python
from pg2_dataset.dataset import Dataset

# Load the dataset from a TOML file
dataset = Dataset.from_toml("path/to/dataset.toml")

# Access the MSA dataset
msa_dataset = dataset.msa
```

For this to work, your dataset.toml file must include an MSA resource:

```toml
[resources]
records = "path/to/records.csv"
structure = "path/to/structure.cif"
msa = "path/to/alignment.a3m"  # Can be .a3m, .a2m, or .psi
```

### 2. Directly Creating an MSADataset

You can also create an `MSADataset` directly:

```python
from pg2_dataset.backends import MSADataset

# Create the dataset with a file path
msa_dataset = MSADataset(file_path="path/to/alignment.a3m")
```

## Accessing MSA Data

Once you've loaded an MSA dataset, you can access the data in several ways:

### Accessing All Sequences

```python
# Get all sequences in the MSA
sequences = msa_dataset.sequences
print(f"Number of sequences in alignment: {len(sequences)}")
print(f"Length of first sequence: {len(sequences[0])}")
```

### Accessing the MSA Dictionary

```python
# Access the raw MSA dictionary (record_name -> sequence)
msa_dict = msa_dataset.msa

# Iterate through all records
for record_name, sequence in msa_dict.items():
    print(f"Record: {record_name}, Sequence length: {len(sequence)}")
```

## Understanding MSA File Parsing

The `MSADataset` class handles the parsing of MSA files through specialized methods for each format:

### A2M Format

A2M files are parsed line by line, with sequences being built up from non-header lines:

```python
# Example of an A2M file:
# >seq1 description
# ABCDEFGHI
# >seq2 description
# ABC--FGHI
```

The parser ensures that all sequences in an A2M file have the same length, which is a requirement for this format.

### A3M Format

A3M files are parsed similarly to A2M files, but without the length validation:

```python
# Example of an A3M file:
# >seq1 description
# ABCDEFGHI
# >seq2 description
# ABCdeFGHI  # lowercase letters represent insertions relative to the query
```

### PSI Format

PSI files have a simpler format where each line contains a header and sequence:

```python
# Example of a PSI file:
# seq1 ABCDEFGHI
# seq2 ABC--FGHI
```

## Record Name Extraction

The `MSADataset` includes a helper method for extracting record names from FASTA headers:

```python
# For a standard FASTA header
record_name = MSADataset._extract_record_name(">sequence1 description")
# record_name = "sequence1 description"

# For a UniProt-style header
record_name = MSADataset._extract_record_name(">tr|A0A1B2C3D4|PROTEIN_NAME description")
# record_name = "A0A1B2C3D4"
```

This ensures consistent record naming regardless of the header format.

## Example Usage

Here's a complete example of working with an MSA dataset:

```python
from pg2_dataset.dataset import Dataset
from pg2_dataset.backends import MSADataset

# Method 1: Load from dataset.toml
dataset = Dataset.from_toml("example_data/dataset.toml")
msa_dataset = dataset.msa

# Method 2: Create directly
# msa_dataset = MSADataset(file_path="path/to/alignment.a3m")

# Check basic information
print(f"Number of sequences: {len(msa_dataset.sequences)}")

# Get the first few sequences
first_sequences = msa_dataset.sequences[:3]
for i, seq in enumerate(first_sequences):
    print(f"Sequence {i+1}: {seq[:50]}...")  # Show first 50 characters

# Find the most common residue at each position
if msa_dataset.sequences:
    seq_length = len(msa_dataset.sequences[0])
    for pos in range(min(10, seq_length)):  # First 10 positions
        residues = [seq[pos] for seq in msa_dataset.sequences if len(seq) > pos]
        residue_counts = {}
        for res in residues:
            residue_counts[res] = residue_counts.get(res, 0) + 1
        
        most_common = max(residue_counts.items(), key=lambda x: x[1])
        print(f"Position {pos+1}: Most common residue is {most_common[0]} ({most_common[1]} occurrences)")
```

## Working with Large MSAs

MSA files can be very large, containing thousands of sequences. Here are some tips for working with large MSAs:

```python
# Load the MSA
msa_dataset = MSADataset(file_path="path/to/large_alignment.a3m")

# Get basic statistics
sequence_count = len(msa_dataset.sequences)
print(f"Total sequences: {sequence_count}")

# Calculate sequence length statistics
lengths = [len(seq) for seq in msa_dataset.sequences]
avg_length = sum(lengths) / len(lengths)
min_length = min(lengths)
max_length = max(lengths)

print(f"Average sequence length: {avg_length:.1f}")
print(f"Minimum sequence length: {min_length}")
print(f"Maximum sequence length: {max_length}")

# Process sequences in batches to avoid memory issues
batch_size = 100
for i in range(0, sequence_count, batch_size):
    batch = msa_dataset.sequences[i:i+batch_size]
    # Process batch...
    print(f"Processed batch {i//batch_size + 1}")
```

## Best Practices

1. **File Format Selection**: Choose the appropriate MSA format based on your needs
   - A2M: When you need guaranteed equal sequence lengths
   - A3M: When working with insertions relative to a query
   - PSI: For simpler, space-separated formats
2. **Memory Management**: Be aware that large MSAs can consume significant memory
3. **Path Configuration**: Use absolute paths or ensure relative paths are correct
4. **Error Handling**: Add try-except blocks when loading MSA files to handle potential format issues

## Troubleshooting

Common issues when working with MSA datasets:

1. **File Not Found**: Ensure the path to your MSA file is correct
2. **Format Errors**: Verify that your file follows the expected format conventions
3. **Inconsistent Sequence Lengths**: For A2M files, all sequences must have the same length
4. **Memory Issues**: Large MSAs may cause memory problems; consider processing data in batches

## Future Developments

The current implementation of `MSADataset` has some limitations:

1. Directory support is not yet implemented
2. Split functionality (train/valid/test) is not yet available
3. Additional MSA formats could be supported in the future

## Summary

The MSA dataset provides a straightforward way to work with multiple sequence alignment data in the PG2 dataset system. By supporting multiple file formats (A2M, A3M, PSI), it allows you to work with alignments from various sources. The simple interface makes it easy to access and analyze the aligned sequences for evolutionary analysis, structure prediction, or other bioinformatics applications.