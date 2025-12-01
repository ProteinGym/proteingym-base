import dataclasses
from collections.abc import Iterator
from enum import StrEnum
from pathlib import Path
from typing import Optional

import requests
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from pydantic import (
    BaseModel,
    ConfigDict,
    FilePath,
    SerializationInfo,
    ValidationInfo,
    field_serializer,
    field_validator,
)


class SequenceFormat(StrEnum):
    """Enumeration for sequence file formats."""

    FASTA = "fasta"
    """Fasta file format for biological sequences (usually amino acid sequences)"""

    FASTQ = "fastq"
    """FASTQ file format for biological sequences (usually nucleotide sequences)"""


class SequenceType(StrEnum):
    """The sequence types."""

    WILD_TYPE = "wild_type"
    """Prevalent form of the gene as found from natural populations"""

    STARTING_SEQUENCE = "starting_sequence"
    """A non-wild-type reference sequence for the design campaign"""

    ENGINEERED_SEQUENCE = "engineered_sequence"
    """A sequence with engineered mutations in them.

    For example, non-WT and not the reference sequence
    """

    CONTROL = "control_sequence"
    """Control sequences with know properties similar to the tested samples"""

    STANDARD = "standard_sequence"
    """Standard sequences used to calibrate and benchmark measurements"""


class SequenceAlphabet(StrEnum):
    """The sequence alphabets."""

    DNA = "DNA"
    """DNA sequences containing ACGT nucleotides"""

    RNA = "RNA"
    """RNA sequence containing ACGU nucleotides"""

    AA = "AA"
    """Amino acid sequence containing the twenty natural occuring nucleotides"""


class SequenceManifestSection(BaseModel):
    """This is the manifest section for Sequences.

    They can be loaded from multiple directories.  This object is used to
    validate the sequence manifest.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_attribute_docstrings=True,
        str_min_length=1,
    )
    """Configuration for the Pydantic model."""

    type: SequenceType | None = None
    """The type of the sequence."""

    alphabet: SequenceAlphabet
    """The alphabet of the sequence."""

    path: FilePath
    """The path to the sequence file."""

    uniprot_id: Optional[str] = None
    """The UniProt identifier for this sequence."""

    taxon_id: Optional[str] = None
    """The taxonomic ID. For precise lookup"""

    taxon_lineage: Optional[str] = None
    """The root of taxonomic lineage information.
    For grouping datasets into main taxons"""

    molecule_name: Optional[str] = None
    """The molecule name."""

    organism: Optional[str] = None
    """The organism information."""

    @field_validator("path", mode="before", check_fields=True)
    def validate_path(cls, path: Path, info: ValidationInfo) -> Path:
        """Optionally, extend the path with the `relative_to_path` from the context."""
        if info.context and info.context.get("relative_to_path"):
            path = info.context["relative_to_path"] / path
        format = path.suffix[1:].lower()
        if format not in SequenceFormat:
            raise ValueError(f"Unsupported sequence format: {format}")
        return path

    @field_serializer("path", check_fields=True)
    def serialize_path(self, path: Path, info: SerializationInfo) -> str:
        """Serialize the path as a Posix path."""
        if info.context and info.context.get("relative_to_path"):
            path = path.relative_to(info.context["relative_to_path"])
        return path.as_posix()

    @field_serializer("type", "alphabet", check_fields=True)
    def _serialize_str_enum(self, str_enum: StrEnum) -> str:
        """Serialize a StrEnum as a string."""
        return str_enum.value


@dataclasses.dataclass
class Sequence:
    """A sequence in the dataset."""

    name: str
    """The name of the sequence."""

    value: Seq
    """The value of the sequence, a Seq object."""

    type: SequenceType
    """The type of the sequence."""

    alphabet: SequenceAlphabet
    """The alphabet of the sequence."""

    description: str | None = None
    """The description of the sequence."""

    uniprot_id: Optional[str] = None
    """The UniProt identifier for this sequence."""

    taxon_id: Optional[str] = None
    """The taxonomic ID. For precise lookup"""

    taxon_lineage: Optional[str] = None
    """The root of taxonomic lineage information.
    For grouping datasets into main taxons"""

    molecule_name: Optional[str] = None
    """The molecule name."""

    organism: Optional[str] = None
    """The organism information."""

    @property
    def uniprot_data(self) -> dict:
        """Get UniProt data if uniprot_id is available and other fields are empty."""
        if (self.uniprot_id and
            not (self.taxon_id or self.taxon_lineage
                 or self.molecule_name or self.organism)):
            try:
                response = requests.get(
                    f"https://rest.uniprot.org/uniprotkb/{self.uniprot_id}",
                    headers={"Accept": "application/json"},
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                taxon_id = data.get("organism", {}).get("taxonId")
                lineage_list = data.get("organism", {}).get("lineage", [])
                taxon_lineage = lineage_list[0] if lineage_list else None
                return {
                    "taxon_id": str(taxon_id) if taxon_id is not None else None,
                    "taxon_lineage": (
                        str(taxon_lineage) if taxon_lineage is not None else None
                    ),
                    "molecule_name": (
                        data.get("proteinDescription", {})
                            .get("recommendedName", {})
                            .get("fullName", {})
                            .get("value")
                    ),
                    "organism": data.get("organism", {}).get("scientificName")
                }
            except Exception:
                return {}
        return {
            "taxon_id": self.taxon_id,
            "taxon_lineage": self.taxon_lineage,
            "molecule_name": self.molecule_name,
            "organism": self.organism
        }

    def __eq__(self, item: "Sequence") -> bool:
        """Implements the equality (==) operator for Sequence.

        For equality, we only look at the sequence value.
        """
        if not isinstance(item, Sequence):
            return False
        return self.value == item.value and self.alphabet == item.alphabet

    def __repr__(self) -> str:
        """Return a string representation of the Sequence object."""
        lines = [f"Sequence(\n\tname='{self.name}',"]
        if self.description:
            desc = (
                self.description[:60] + "..."
                if len(self.description) > 60
                else self.description
            )
            lines.append(f"\tdescription: {desc},")
        else:
            lines.append("\tdescription: None,")

        lines.append(f"\ttype: {self.type},")
        lines.append(f"\talphabet: {self.alphabet},")

        if self.uniprot_id:
            lines.append(f"\tuniprot_id: {self.uniprot_id},")
        if self.taxon_id:
            lines.append(f"\ttaxon_id: {self.taxon_id},")
        if self.taxon_lineage:
            lines.append(f"\ttaxon_lineage: {self.taxon_lineage},")
        if self.molecule_name:
            lines.append(f"\tmolecule_name: {self.molecule_name},")
        if self.organism:
            lines.append(f"\torganism: {self.organism},")

        value_str = str(self.value)
        if len(value_str) > 60:
            value_str = value_str[:60] + "..."
        lines.append(f"\tvalue: {value_str},")
        lines.append(")")
        return "\n".join(lines)

    @classmethod
    def from_manifest_section(
        cls, section: SequenceManifestSection
    ) -> Iterator["Sequence"]:
        """Create Sequence(s) from a sequence manifest section.

        Args:
            section (SequenceManifestSection): The sequence manifest section to create
                the Sequence from.

        Yields:
            Sequence: The created Sequence object.
        """
        sequences = SeqIO.parse(section.path, format=section.path.suffix[1:].lower())
        for i, seq in enumerate(sequences):
            sequence = cls(
                name=seq.name if seq.name else f"{section.path.stem}_{i}",
                value=seq.seq,
                description=seq.description,
                type=section.type,
                alphabet=section.alphabet,
                uniprot_id=section.uniprot_id,
                taxon_id=section.taxon_id,
                taxon_lineage=section.taxon_lineage,
                molecule_name=section.molecule_name,
                organism=section.organism,
            )

            if (section.uniprot_id and
                not (section.taxon_id or section.taxon_lineage or
                     section.molecule_name or section.organism)):
                uniprot_data = sequence.uniprot_data
                sequence.taxon_id = uniprot_data.get("taxon_id")
                sequence.taxon_lineage = uniprot_data.get("taxon_lineage")
                sequence.molecule_name = uniprot_data.get("molecule_name")
                sequence.organism = uniprot_data.get("organism")

            yield sequence

    def as_manifest_section(self, *, path: Path) -> SequenceManifestSection:
        """Convert the sequence to a manifest section.

        Args:
            path (Path): The path to the sequence file (as created by
                `method:dump`).

        Returns:
            SequenceManifestSection: The manifest section for the sequence.
        """
        current_data = self.uniprot_data
        return SequenceManifestSection(
            path=path,
            alphabet=self.alphabet,
            type=self.type,
            uniprot_id=self.uniprot_id,
            taxon_id=current_data.get("taxon_id") or self.taxon_id,
            taxon_lineage=current_data.get("taxon_lineage") or self.taxon_lineage,
            molecule_name=current_data.get("molecule_name") or self.molecule_name,
            organism=current_data.get("organism") or self.organism,
        )

    def dump(
        self, *, path: Path | None = None, format: SequenceFormat = SequenceFormat.FASTA
    ) -> Path:
        """Dump the sequence to a file in `path` directory.

        Biopython is used for writing the sequence to a file. The following
        formats are supported:
        - FASTA (.fasta)
        - FASTQ (.fastq)

        Args:
            path (Path): The output directory path to dump the sequence to. If
                None, the current working directory is used.
            format (SequenceFormat): The format to dump the sequence in.

        Raises:
            ValueError: If the path does not have a valid sequence file extension.
        """
        if format not in SequenceFormat:
            raise ValueError(f"Unsupported sequence format: {format}")
        path = path or Path.cwd()
        if path.is_dir():
            path = path / f"{self.name}.{format.value}"
        record = SeqRecord(
            seq=self.value, id=self.name, name=self.name, description=self.description
        )
        SeqIO.write(record, path, format.value)
        return path
