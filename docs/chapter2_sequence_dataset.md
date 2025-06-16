# Chapter 2: Creating and Using a Sequence Dataset

## Introduction

The sequence dataset is a fundamental component of the PG2 dataset system, implemented through the `AssaysDataset` class. It provides functionality for working with biological sequence data and associated measurements (assays). This chapter explains how to create, load, and use sequence datasets in your projects.

## Understanding the AssaysDataset

The `AssaysDataset` class is designed to handle sequence data along with various measurements or assays performed on those sequences. It provides methods for:

1. Loading data from CSV files
2. Accessing sequences and their associated measurements
3. Splitting data into training, validation, and test sets
4. Filtering data by specific targets or engineering rounds

## Creating a Sequence Dataset

There are two main ways to create a sequence dataset:

### 1. From a dataset.toml File

The most common approach is to create a sequence dataset through a `dataset.toml` file:

```python
from pg2_dataset.dataset import Dataset

# Load the dataset from a TOML file
dataset = Dataset.from_toml("path/to/dataset.toml")

# Access the sequence dataset
sequence_dataset = dataset.assays
```

### 2. Directly Creating an AssaysDataset

You can also create an `AssaysDataset` directly:

```python
from pg2_dataset.backends import AssaysDataset
from pg2_dataset.primitives.meta import AssaysMeta, SingleAssayMeta

# Create metadata for assays
assays_meta = AssaysMeta(
    file_path="path/to/data.csv",
    sequence_feature="sequence_column",
    assays={
        "binding_affinity": SingleAssayMeta(
            description="Protein binding affinity measurement",
            features=["pH", "temperature"]
        )
    }
)

# Create the dataset
sequence_dataset = AssaysDataset(meta=assays_meta)
```

## Data Structure

The sequence dataset organizes data into several key components:

### Records

Each record represents a single sequence and its associated measurements:

```python
# Access all records in the dataset
records = sequence_dataset.records

# Example of a single record
record = records[0]
print(record.sequence)  # The sequence string
print(record.engineering_round)  # Engineering round number
```

The `Record` class is a Pydantic model that includes:
- `sequence`: The biological sequence (required)
- `engineering_round`: Round number (defaults to 1)
- Additional fields for measurements and features

### DataFrame Access

You can access the data as a pandas DataFrame:

```python
# Get the full DataFrame
df = sequence_dataset.data_frame

# Get DataFrame filtered by a specific target
target_df = sequence_dataset.data_frame_by_target("binding_affinity")
```

## Working with Data Splits

The sequence dataset provides functionality for splitting data into training, validation, and test sets:

### Adding a Split Strategy

```python
from pg2_dataset.splits import RandomSplitStrategy

# Create a split strategy (80% train, 20% validation)
split_strategy = RandomSplitStrategy(train_ratio=0.8, valid_ratio=0.2)

# Add the split to the dataset
sequence_dataset.add_split(
    split_strategy=split_strategy,
    targets=["binding_affinity"],  # Specific targets to consider
    round_num=1  # Engineering round to consider
)
```

### Accessing Split Data

Once splits are defined, you can access the different subsets:

```python
# Get training data
train_data = sequence_dataset.train()
train_x, train_y = train_data.x, train_data.y

# Get validation data
valid_data = sequence_dataset.valid()
valid_x, valid_y = valid_data.x, valid_data.y

# Get test data
test_data = sequence_dataset.test()
test_x, test_y = test_data.x, test_data.y

# Get splits for specific targets
train_data_specific = sequence_dataset.train(targets=["binding_affinity"])
```

## Working with Engineering Rounds

Many biological datasets involve multiple rounds of engineering or experimentation. The sequence dataset provides methods to work with this structure:

```python
# Iterate through datasets by engineering round
for round_df in sequence_dataset.iter_by_rounds():
    print(f"Round data shape: {round_df.shape}")
    
# Limit to a maximum round
for round_df in sequence_dataset.iter_by_rounds(max_round=2):
    print(f"Round data shape: {round_df.shape}")
```

## Data Transformation

The sequence dataset handles several data transformations automatically:

### Column Renaming

The dataset automatically renames columns from your CSV to standardized internal names:
- Your sequence column → `"sequence"`
- Your engineering round column → `"engineering_round"`
- Your split column → `"split"`

### Default Values

If certain information is missing:
- Engineering round defaults to 1 if not specified
- Each record gets a unique UUID for tracking

## Example Usage

Here's a complete example of working with a sequence dataset:

```python
from pg2_dataset.dataset import Dataset
from pg2_dataset.splits import RandomSplitStrategy

# Load dataset from TOML
dataset = Dataset.from_toml("example_data/dataset.toml")
sequence_dataset = dataset.assays

# Examine the data
print(f"Number of records: {len(sequence_dataset.records)}")
print(f"Available targets: {sequence_dataset.targets}")
print(f"Available features: {sequence_dataset.features}")

# Create a data split
split_strategy = RandomSplitStrategy(train_ratio=0.7, valid_ratio=0.15)
sequence_dataset.add_split(split_strategy)

# Get training and validation data
train_data = sequence_dataset.train()
valid_data = sequence_dataset.valid()
test_data = sequence_dataset.test()

print(f"Training samples: {len(train_data)}")
print(f"Validation samples: {len(valid_data)}")
print(f"Test samples: {len(test_data)}")

# Access the data
X_train, y_train = train_data.x, train_data.y
```

## Best Practices

1. **Data Quality**: Ensure your CSV data has consistent formatting and no missing values in critical columns
2. **Column Naming**: Use clear, consistent naming for sequence and measurement columns
3. **Split Strategies**: Choose appropriate split strategies based on your data characteristics
4. **Engineering Rounds**: If your data involves multiple rounds, ensure the round column is properly specified
5. **Target Selection**: When working with splits, specify only the targets relevant to your analysis

## Troubleshooting

Common issues when working with sequence datasets:

1. **Missing Sequence Data**: Ensure your CSV has a valid sequence column specified in the TOML file
2. **Split Errors**: If you get errors about missing splits, make sure to call `add_split()` before accessing train/valid/test data
3. **Column Mismatch**: Verify that columns specified in your TOML file match those in your CSV
4. **Data Type Errors**: Ensure your measurement data has appropriate types (numeric for measurements, strings for sequences)

## Summary

The sequence dataset provides a powerful and flexible way to work with biological sequence data and associated measurements. By properly configuring your dataset through a TOML file or direct initialization, you can easily load, transform, and split your data for analysis and machine learning tasks.