### Data Manifest Schema
This schema defines the structure of a dataset that is required to create pg2-datasets for the ProteinGYM2 framework. The datasets are comprised of four types of data: sequences, structures, multiple sequence alignments (MSAs), and assays. 

When creating a new pg2-dataset, dataset creator will supply as .toml manifest file which contains the information required to load the data objects. The datatypes (sequences, structures, MSAs, and assays) are defined as separate sub-classes with their own metadata and file handling methods.

The schema is designed for enabling:
1. Consistency: Ensure all the datasets follow the same structure.
2. Compatibility: Allow the framework to load and process datasets automatically.
3. Extensibility: Allow for future additions without breaking existing datasets.
4. Clarity: Provide a clear understanding of the dataset components.


### Definitions
1. **Dataset:** It is a collection of biological data that are used for benchmarking pg2-models with pg2-benchmark framework. This class contains the metadata of the dataset, and the references to the sequences, structures, MSAs, and assays data types. Dataset class also contains the assay conditions defined in section 6. 

2. **DataGetter:** It is a class that handles the retrieval of data from either a local directory or a cross-reference (xref) to an external database. The data recieved is then used by data factories. DataGetter must have either a valid directory path or a cross-reference to fetch the data. 
    
    - **DataDir:** It represents a directory where the data files are stored. It can be either the working directory or a cloud storage like SFTP servers, s3 buckets, etc. 
    
    - **CrossRef:** It represents a cross-reference to an external database. The CrossRef class contains information about the external database and provides methods to retrieve data from it.
    
    - **DataType:** The pg2-dataset module supports four data types given in Dataset definition.

3. **Sequence:** It represents a biological sequence. These sequences are the base sequences which are used in curation of other data types like assays, structures, msas. 

    - **SequenceFactory:** It uses the DataGetter object to generate Sequence objects. The data loaded from the DataGetter is validated before generating the Sequence objects. 

    - **SequenceAlphabet:** There are three types of sequence alphabets: DNA, RNA, AA.

    - **SequenceType:** The pg2-dataset module supports three sequence types: WILD_TYPE, STARTING_SEQUENCE, ENGINEERED_SEQUENCE.

    - **SequenceFileType:** When using DataDir, FASTA file types are supported.

4. **Structure:** It represents the 2d/3d structure of a protein or nucleic acid. These structures are used in the curation of other data types like assays and MSAs.
    
    - **StructureFactory:** It uses the DataGetter object to generate Structure objects.
    
    - **StructureFileType:** The pg2-dataset module supports three structure file types: PDB, CIF, and mmCIF.

5. **MSA:** It is the multi sequence alignment data.

    - **MSAFactory:** It uses the DataGetter object to generate MSA objects.

    - **MSAFileType:** The pg2-dataset module supports three MSA file types: A3M, A2M, and PSI.

6. **Assay:** Assays are experimental data that contains modified or mutated sequences and corresponding values for targets. It is a supervised dataset where X is the modified sequences and Y is the target value. In addition to the sequences, assays also contain assay conditions. These conditions are biological factors that impact the assay results. For an assay, the assay conditions are kept constant and the target value is measured for the modified sequences.
    - **AssayFactory:** It uses the DataGetter object to generate Assay objects.

    - **AssayCondition:** It represents the conditions under which the assay was performed. These conditions can include factors like temperature, pH, and other experimental variables. These conditions are constant for an assay.

    - **AssayRecord:** It contains the sequence and the corresponding target value for the assay. Each record represents a single data point in the assay. Assay is created from a list of AssayRecord class instances.

    - **AssayTarget:** It contains the metadata of the target value for the assay.

    - **AssayDataType:** It represents the type of data in the assay: Categorical, Numerical, and Boolean.

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
        +string name
        +object value
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
        +string name
        +object value
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
        +string name
        +AssayRecord[] records
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
        +AssayDataType data_type
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
    AssayTarget o-- AssayDataType

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

