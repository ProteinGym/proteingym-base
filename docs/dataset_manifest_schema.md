### Data Manifest Schema
This schema defines the structure of a dataset that is required to be compatible with the ProteinGYM2 framework. The datasets are comprised of four types of data: sequences, structures, multiple sequence alignments (MSAs), and assays. Each dataset is represented by a `Dataset` class that contains metadata and references to the various components. The datatypes (sequences, structures, MSAs, and assays) are defined as separate classes with their own metadata and file handling methods.

#### Motivation
The schema is designed for enabling:
1. Consistency: Ensure all the datasets follow the same structure.
2. Compatibility: Allow the framework to load and process datasets automatically.
3. Extensibility: Allow for future additions without breaking existing datasets.
4. Clarity: Provide a clear understanding of the dataset components.



```mermaid
classDiagram
    class Dataset {
        +string name
        +string description
        +string version
        +Sequences sequences
        +Structures structures
        +MSAs msas
        +Assays assays
        +string doi
        +string creator   
        +string xref
        +dict metadata
        +func loader() 
    }
    class DatasetType {
        <<enumeration>>
        +string sequence
        +string structure
        +string msa
        +string assay
        +func type_handler()
    }
    class DatasetDir {
        +string dir_path
        +DatasetType data_type
        +func get_files()
    }


    class Sequences {
        +SequenceFiles file_path
        +string description
        +SequenceType sequence_type
        +string doi
        +dict metadata
        +func dir_or_file_exists()
        +func validate_sequence_type()
        +func biopython_loader()
    }
    class SequenceType {
        <<enumeration>>
        +string DNA
        +string RNA
        +string AA
        +func type_handler()
    }
    class SequenceFiles {
        +DatasetDir dir_path
        +string[] file_path
        +SequenceFileType file_type
        +func file_handler()
    }
    class SequenceFileType {
        <<enumeration>>
        +string FASTA
        +func type_handler()
    }

    class Structures {
        +StructureFiles file_path
        +string description
        +string doi
        +dict metadata
        +func biopython_loader()
    }
    class StructureFiles {
        +DatasetDir dir_path
        +string[] file_path
        +StructureFileType file_type
        +func file_handler()
    }
    class StructureFileType {
        <<enumeration>>
        +string PDB
        +string CIF
        +string binaryCIF
        +func type_handler()
    }


    class MSAs {
        +MSAFiles file_path
        +string description
        +dict metadata
        +func biopython_loader()
    }
    class MSAFiles {
        +DatasetDir dir_path
        +string[] file_path
        +MSAFileType file_type
        +func file_handler()
    }
    class MSAFileType {
        <<enumeration>>
        +string A3M
        +string A2M
        +string PSI
        +func type_handler()
    }


    class Assays {
        +AssayFiles file_path
        +string description
        +AssayMetadata metadata
        +AssayTarget[] targets
        +func biopython_loader()
        +func dataset_by_assay_target(target)
    }
    class AssayMetadata {
        +string[] feature_names
        +string modified_sequence_feature_name
        +string split_feature_name
        +string engineering_round_feature_name
        +string doi
        +dict metadata
    }
    class AssayFiles {
        +DatasetDir dir_path
        +string[] file_path
        +AssayFileType file_type
        +func file_handler()
        }
    class AssayFileType {
        <<enumeration>>
        +string CSV
        +func type_handler()
    }
    class AssayTarget {
        +string target_name
        +string[] feature_names
        +func validator()
    }

    Dataset "1" o-- "1" Sequences
    Dataset "1" o-- "0..*" Structures
    Dataset "1" o-- "0..*" MSAs
    Dataset "1" o-- "0..*" Assays
    Sequences o-- SequenceType
    Sequences "1" o-- "*" SequenceFiles
    Structures "1" o-- "*" StructureFiles
    MSAs "1" o-- "*" MSAFiles
    Assays o-- AssayMetadata
    Assays "1" o-- "*" AssayFiles
    StructureFiles o-- StructureFileType
    SequenceFiles o-- SequenceFileType
    AssayFiles o-- AssayFileType
    MSAFiles o-- MSAFileType
    Assays "1" o-- "*" AssayTarget
    AssayFiles o-- DatasetDir
    SequenceFiles o-- DatasetDir
    StructureFiles o-- DatasetDir
    MSAFiles o-- DatasetDir
    DatasetDir o-- DatasetType
```