"""Sklearn transformers for assay dataframes.

This module provides sklearn-compatible transformers for converting assay
dataframes to feature matrices (X) and target vectors (y).
"""
# Ignore argument and variable `X` in function should be lowercase
# ruff: noqa: N803, N806

# PyCharm: Suppress PEP 8 naming warnings for sklearn transformer methods
# noinspection PyPep8Naming

from __future__ import annotations

import numpy as np
import pandas as pd
import polars as pl
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .dataset import Dataset


class SequenceOneHotEncoder(BaseEstimator, TransformerMixin):
    """One-hot encoder for sequences.

    The encoder learns the alphabet from the training data. All sequences
    must be the same length. An error will be raised if sequences have
    varying lengths.
    """

    def __init__(self) -> None:
        self.alphabet_: list[str] = []
        self.max_length_: int = 0
        self.char_to_idx_: dict[str, int] = {}
        self.variant_columns_: np.ndarray | None = None

    def fit(
        self, X: pl.DataFrame | pd.DataFrame | pd.Series | Dataset
    ) -> SequenceOneHotEncoder:
        """Learn the alphabet and sequence length from the training data.

        Args:
            X: Input data containing sequences. Can be a Polars DataFrame, Pandas
                DataFrame, Pandas Series, or Dataset. All sequences must have the
                same length.

        Returns:
            Fitted encoder.

        Raises:
            ValueError: If sequences have varying lengths.
        """
        if isinstance(X, Dataset):
            X = X.to_df()["sequence"]

        # Flatten to 1D array
        sequences = X.to_numpy().ravel()

        chars = set()
        lengths = set()
        for seq in sequences:
            seq_str = str(seq)
            chars.update(seq_str)
            lengths.add(len(seq_str))

        if len(lengths) > 1:
            msg = (
                f"All sequences must have the same length. "
                f"Found sequences with lengths: {sorted(lengths)}"
            )
            raise ValueError(msg)

        self.alphabet_ = sorted(chars)
        self.max_length_ = lengths.pop() if lengths else 0
        self.char_to_idx_ = {char: idx for idx, char in enumerate(self.alphabet_)}

        n_samples = len(sequences)
        alphabet_size = len(self.alphabet_)
        encoding_size = self.max_length_ * alphabet_size

        encoded = np.zeros((n_samples, encoding_size), dtype=np.float64)

        for i, seq in enumerate(sequences):
            seq_str = str(seq)
            for pos, char in enumerate(seq_str):
                if char in self.char_to_idx_:
                    char_idx = self.char_to_idx_[char]
                    flat_idx = pos * alphabet_size + char_idx
                    encoded[i, flat_idx] = 1.0

        # Identify columns with variance (non-constant columns)
        # A column is variant if it has more than one unique value
        self.variant_columns_ = np.var(encoded, axis=0) > 0

        return self

    def transform(
        self, X: pl.DataFrame | pd.DataFrame | pd.Series | Dataset
    ) -> np.ndarray:
        """Transform sequences to one-hot encoded matrix.

        Args:
            X: Input data containing sequences. Can be a Polars DataFrame, Pandas
                DataFrame, Pandas Series, or Dataset. All sequences must have the
                same length as the sequences used during fitting.

        Returns:
            One-hot encoded matrix of shape (n_samples, n_variant_features).
                Each sequence is encoded as a flattened matrix where position i and
                character j are encoded at index (i * alphabet_size + j).
                Invariant (constant) columns are removed.

        Raises:
            ValueError: If sequences have varying lengths or don't match the expected
                length from fitting.
        """
        if isinstance(X, Dataset):
            X = X.to_df()["sequence"]

        # Flatten to 1D array
        sequences = X.to_numpy().ravel()

        lengths = set()
        for seq in sequences:
            seq_str = str(seq)
            lengths.add(len(seq_str))

        if len(lengths) > 1:
            msg = (
                f"All sequences must have the same length. "
                f"Found sequences with lengths: {sorted(lengths)}"
            )
            raise ValueError(msg)

        actual_length = lengths.pop() if lengths else 0
        if actual_length != self.max_length_:
            msg = (
                f"Expected sequences of length {self.max_length_} "
                f"(from training data), but got sequences of length {actual_length}"
            )
            raise ValueError(msg)

        n_samples = len(sequences)
        alphabet_size = len(self.alphabet_)
        encoding_size = self.max_length_ * alphabet_size

        encoded = np.zeros((n_samples, encoding_size), dtype=np.float64)

        for i, seq in enumerate(sequences):
            seq_str = str(seq)
            for pos, char in enumerate(seq_str):
                if char in self.char_to_idx_:
                    char_idx = self.char_to_idx_[char]
                    flat_idx = pos * alphabet_size + char_idx
                    encoded[i, flat_idx] = 1.0

        # Apply variant column mask to remove invariant features
        if self.variant_columns_ is not None:
            encoded = encoded[:, self.variant_columns_]

        return encoded

    def get_feature_names_out(self, input_features: list[str]) -> np.ndarray:
        """Get output feature names for transformation.

        Args:
            input_features: Input feature names.

        Returns:
            Array of feature names in the format: column_pos{i}_{char}.
                Only includes features for variant (non-constant) columns.
        """
        feature_names = []
        for pos in range(self.max_length_):
            for char in self.alphabet_:
                feature_names.append(f"{input_features[0]}_pos{pos}_{char}")

        feature_names_array = np.array(feature_names)

        # Apply variant column mask to only return variant feature names
        if self.variant_columns_ is not None:
            feature_names_array = feature_names_array[self.variant_columns_]

        return feature_names_array


class AssayTransformer(BaseEstimator, TransformerMixin):
    """Sklearn ColumnTransformer for converting assay dataframes to X and y matrices.

    This transformer handles the common case of transforming assay dataframes into
    feature matrices (X) and target vectors (y) suitable for machine learning.

    Features (X) are transformed as follows:
    - Sequence column: One-hot encoded using SequenceOneHotEncoder
    - Categorical variables: One-hot encoded using sklearn's OneHotEncoder
    - Numerical variables: Standardized using sklearn's StandardScaler

    Targets (y) are extracted without transformation.

    Example:
        >>> import polars as pl
        >>> from proteingym.base.transformers import AssayTransformer
        >>>
        >>> df = pl.DataFrame({
        ...     "sequence": ["ABC", "DEF"],
        ...     "DMS Score": [0.8, 0.6],
        ...     "condition": ["A", "A"],
        ...     "temperature": [37, 37]
        ... })
        >>>
        >>> transformer = AssayTransformer(
        ...     sequence_column="sequence",
        ...     target_columns=["DMS Score"],
        ...     categorical_columns=["condition"],
        ...     numerical_columns=["temperature"]
        ... )
        >>>
        >>> X, y = transformer.fit_transform(df)
        >>>
        >>> assert X.shape == (2, 8)
        >>> assert y.shape == (2,)
    """

    def __init__(
        self,
        sequence_column: str = "sequence",
        target_columns: list[str] | None = None,
        categorical_columns: list[str] | None = None,
        numerical_columns: list[str] | None = None,
    ) -> None:
        """Initialize the AssayTransformer.

        Args:
            sequence_column: Name of the column containing biological sequences.
                Defaults to "sequence".
            target_columns: Names of target columns to extract as y.
                Required unless using from_dataset().
            categorical_columns: Names of categorical variable columns
                to one-hot encode.
            numerical_columns: Names of numerical variable columns
                to standardize.
        """
        self.sequence_column = sequence_column
        self.target_columns = target_columns or []
        self.categorical_columns = categorical_columns
        self.numerical_columns = numerical_columns
        self.column_transformer_: ColumnTransformer | None = None
        self.feature_names_: list[str] = []

    @classmethod
    def from_dataset(
        cls,
        dataset: Dataset,
        categorical_variables: list[str] | None = None,
        numerical_variables: list[str] | None = None,
    ) -> AssayTransformer:
        """Create an AssayTransformer from a Dataset.

        Args:
            dataset: The Dataset to create the transformer from.
            categorical_variables: Names of categorical variables to one-hot encode.
                If None, all string/bool variables are treated as categorical.
            numerical_variables: Names of numerical variables to standardize.
                If None, all int/float variables are treated as numerical.

        Returns:
            An initialized AssayTransformer.
        """
        target_columns = [target.name for target in dataset.assay_targets]

        # Infer categorical columns if not provided
        if categorical_variables is None:
            categorical_variables = []

            for var in dataset.assay_variables:
                if var.value is not None and isinstance(var.value, (bool, str)):
                    categorical_variables.append(var.name)

        # Infer numerical columns if not provided
        if numerical_variables is None:
            numerical_variables = []

            for var in dataset.assay_variables:
                if var.value is not None and isinstance(var.value, (int, float)):
                    numerical_variables.append(var.name)

        return cls(
            sequence_column="sequence",
            target_columns=target_columns,
            categorical_columns=categorical_variables,
            numerical_columns=numerical_variables,
        )

    def fit(self, X: pl.DataFrame | Dataset) -> AssayTransformer:
        """Fit the transformer on the training data.

        Args:
            X: Input data containing sequences, variables, and targets. Can be a
                Polars DataFrame or Dataset.

        Returns:
            Fitted transformer.
        """
        if isinstance(X, Dataset):
            X = X.to_df()

        transformers: list[tuple[str, BaseEstimator | str, list[str]]] = [
            (self.sequence_column, SequenceOneHotEncoder(), [self.sequence_column])
        ]

        if self.categorical_columns:
            for categorical_column in self.categorical_columns:
                transformers.append(
                    (
                        categorical_column,
                        OneHotEncoder(sparse_output=False, handle_unknown="ignore"),
                        [categorical_column],
                    )
                )

        if self.numerical_columns:
            for numerical_column in self.numerical_columns:
                transformers.append(
                    (numerical_column, StandardScaler(), [numerical_column])
                )

        self.column_transformer_ = ColumnTransformer(
            transformers=transformers,
            remainder="drop",  # Drop target columns
        )

        feature_columns = [col for col in X.columns if col not in self.target_columns]
        X_features = X.select(feature_columns)

        # sklearn's ColumnTransformer needs pandas DataFrame when using column names
        X_features_pandas = X_features.to_pandas()

        self.column_transformer_.fit(X_features_pandas)

        self.feature_names_ = self._get_feature_names()

        return self

    def transform(self, X: pl.DataFrame | Dataset) -> tuple[np.ndarray, np.ndarray]:
        """Transform the dataframe to feature matrix X and target vector y.

        Args:
            X: Input data containing sequences, variables, and targets. Can be a
                Polars DataFrame or Dataset.

        Returns:
            Tuple of (X, y) where:
            - X is the transformed feature matrix of shape (n_samples, n_features)
            - y is the target vector/matrix of shape (n_samples,)
                or (n_samples, n_targets)
        """
        if isinstance(X, Dataset):
            X = X.to_df()

        if self.column_transformer_ is None:
            msg = "Transformer has not been fitted. Call fit() first."
            raise ValueError(msg)

        feature_columns = [col for col in X.columns if col not in self.target_columns]
        X_features = X.select(feature_columns)
        y_targets = X.select(self.target_columns).to_numpy()

        # Convert to pandas for sklearn compatibility
        X_features_pandas = X_features.to_pandas()

        X_transformed = self.column_transformer_.transform(X_features_pandas)

        # Squeeze y if single target
        if y_targets.shape[1] == 1:
            y_targets = y_targets.ravel()

        return X_transformed, y_targets

    def _get_feature_names(self) -> list[str]:
        """Get feature names from the fitted transformer.

        Returns:
            List of feature names after transformation.
        """
        if self.column_transformer_ is None:
            return []

        feature_names = []
        for name, transformer, columns in self.column_transformer_.transformers_:
            if name == "remainder":
                continue

            if name == self.sequence_column:
                if hasattr(transformer, "get_feature_names_out"):
                    seq_features = transformer.get_feature_names_out([name])
                    feature_names.extend(seq_features)
            elif self.categorical_columns and name in self.categorical_columns:
                if hasattr(transformer, "get_feature_names_out"):
                    cat_features = transformer.get_feature_names_out(columns)
                    feature_names.extend(cat_features)
            elif self.numerical_columns and name in self.numerical_columns:
                feature_names.extend(columns)

        return feature_names

    def get_feature_names_out(self, input_features: list[str] = None) -> np.ndarray:
        """Get output feature names for transformation.

        Args:
            input_features: Ignored. Present for API consistency with sklearn.

        Returns:
            Array of feature names.
        """
        return np.array(self.feature_names_)
