### Data Manifest Schema
This schema defines the structure of a dataset that is required to be compatible with the ProteinGYM2 framework. The datasets are comprised of four types of data: sequences, structures, multiple sequence alignments (MSAs), and assays. Each dataset is represented by a `Dataset` class that contains metadata and references to the various components. The datatypes (sequences, structures, MSAs, and assays) are defined as separate classes with their own metadata and file handling methods.

The schema is designed for enabling:
1. Consistency: Ensure all the datasets follow the same structure.
2. Compatibility: Allow the framework to load and process datasets automatically.
3. Extensibility: Allow for future additions without breaking existing datasets.
4. Clarity: Provide a clear understanding of the dataset components.


Class Diagram:

```mermaid
classDiagram
    class Dataset {
        +string name
        +string description
        +string version
        +Sequence[] sequences
        +Structure[] structures
        +MSA[] msas
        +Assay[] assays
        +AssayCondition[] assay_conditions
        +string creator   
        +string xref
        +dict metadata
        +func loader() 
    }
    class DataGetter {
        +DataDir dir_path
        +CrossRef xref
        +DataType data_type
        +func datadir_or_xref_exists()
        +func get_data()
    }
    class DataType {
        <<enumeration>>
        +string sequence
        +string structure
        +string msa
        +string assay
        +func type_handler()
    }
    class DataDir {
        +string dir_path
        +DirType dir_type
        +func get_files()
    }
    class DirType {
        <<enumeration>>
        +string s3
        +string local
        +func type_handler()
    }
    class CrossRef {
        +string xref
        +string description
        +CrossRefType xref_type
        +func xref_handler()
    }
    class CrossRefType {
        <<enumeration>>
        +string UniProt
        +string Benchling
        +string RCSB
        +string doi
        +func type_handler()
    }

    class Sequence {
        +string value
        +string description
        +SequenceType sequence_type
        +SequenceAlphabet alphabet
        +dict metadata
        +func validate_sequence()
        +func biopython_loader()
    }
    class SequenceFactory {
        +DataGetter loader
        +func validate()
        +func generate_sequences()
    }
    class SequenceAlphabet {
        <<enumeration>>
        +string DNA
        +string RNA
        +string AA
        +func type_handler()
    }
    class SequenceType {
        <<enumeration>>
        +string WILD_TYPE
        +string STARTING_SEQUENCE
        +string ENGINEERED_SEQUENCE
        +func type_handler()
    }
    class SequenceFileType {
        <<enumeration>>
        +string FASTA
        +func type_handler()
    }

    class Structure {
        +string description
        +dict metadata
        +func validate_structure()
        +func biopython_loader()
    }
    class StructureFactory {
        +DataGetter loader
        +func validate()
        +func generate_structures()
    }
    class StructureFileType {
        <<enumeration>>
        +string PDB
        +string CIF
        +string binaryCIF
        +func type_handler()
    }


    class MSA {
        +string description
        +dict metadata
        +func biopython_loader()
    }
    class MSAFactory {
        +DataGetter loader
        +func validate()
        +func generate_msas()
    }
    class MSAFileType {
        <<enumeration>>
        +string A3M
        +string A2M
        +string PSI
        +func type_handler()
    }


    class Assay {
        +AssayRecord[] row_data 
        +string description
        +dict AssayCondition.AssayDataType: condition_values
        +AssayTarget target
        +func biopython_loader()
        +func dataset_by_assay_target(target)
    }
    class AssayRecord {
        +Sequence sequence
        +AssayTarget.DataType value
    }
    class AssayCondition {
        +string name
        +string unit
        +AssayDataType data_type
        +string description
        +func validate_condition()
    }
    class AssayDataType {
        <<enumeration>>
        +string Categorical
        +string Numerical
        +string Boolean
    }
    class AssayFactory {
        +DataGetter loader
        +func validate()
        +func generate_assays()
    }
    class AssayFileType {
        <<enumeration>>
        +string CSV
        +func type_handler()
    }
    class AssayTarget {
        +string target_name
        +string unit
        +string description
        +DataType data_type
        +func validator()
    }

    Dataset "1" o-- "1" Sequence
    Dataset "1" o-- "0..*" Structure
    Dataset "1" o-- "0..*" MSA
    Dataset "1" o-- "0..*" Assay
    Dataset "1" o-- "0..*" AssayCondition
    Sequence o-- SequenceFactory
    Sequence o-- SequenceAlphabet
    Sequence o-- SequenceType
    SequenceFactory "1" o-- "*" DataGetter

    Structure "1" o-- "*" StructureFactory
    StructureFactory "1" o-- "*" DataGetter

    MSA "1" o-- "*" MSAFactory
    MSAFactory "1" o-- "*" DataGetter

    Assay o-- AssayFactory
    AssayFactory "1" o-- "*" DataGetter
    Assay o-- AssayTarget
    Assay o-- AssayRecord
    Assay o-- AssayCondition
    AssayCondition o-- AssayDataType
    DataGetter o-- DataType
    DataGetter o-- CrossRef
    DataGetter o-- DataDir
    DataDir o-- DirType

    CrossRef o-- CrossRefType

    DataDir o-- SequenceFileType
    DataDir o-- StructureFileType
    DataDir o-- MSAFileType
    DataDir o-- AssayFileType
```
**Note**

1. Biopython can be replaced with Biotite

Future To-Do:
1. Sequences can be constructed from public databases like https://www.rcsb.org/, https://www.uniprot.org/, Benchling, etc.
2. Out of Scope: Connecting to internal IFF databases like LIMS, IFF-Benchling etc.

