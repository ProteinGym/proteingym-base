"""Sklearn transformers for assay dataframes.

This module provides sklearn-compatible transformers for converting assay
dataframes to feature matrices (X) and target vectors (y).
"""
# Ignore argument and variable `X` in function should be lowercase
# ruff: noqa: N803, N806

from __future__ import annotations

import numpy as np
import polars as pl
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler


class SequenceOneHotEncoder(BaseEstimator, TransformerMixin):
    """One-hot encoder for sequences.

    The encoder learns the alphabet from the training data and can handle
    sequences of varying lengths by padding shorter sequences with zeros.
    """

    def __init__(self) -> None:
        self.alphabet_: list[str] = []
        self.max_length_: int = 0
        self.char_to_idx_: dict[str, int] = {}

    def fit(self, X: np.ndarray) -> SequenceOneHotEncoder:
        """Learn the alphabet and maximum sequence length from the training data.

        Args:
            X: Input data containing sequences. Should be a numpy ndarray that is 1D or
                2D with shape (n_samples, 1).

        Returns:
            Fitted encoder.
        """
        # Handle pandas DataFrame/Series
        if hasattr(X, "to_numpy"):
            X = X.to_numpy()

        # Flatten to 1D array
        sequences = X.ravel() if isinstance(X, np.ndarray) else X

        chars = set()
        max_len = 0
        for seq in sequences:
            seq_str = str(seq)
            chars.update(seq_str)
            max_len = max(max_len, len(seq_str))

        self.alphabet_ = sorted(chars)
        self.max_length_ = max_len
        self.char_to_idx_ = {char: idx for idx, char in enumerate(self.alphabet_)}

        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Transform sequences to one-hot encoded matrix.

        Args:
            X: Input data containing sequences. Should be a numpy ndarray that is 1D or
                2D with shape (n_samples, 1).

        Returns:
            One-hot encoded matrix of shape (n_samples, max_length * alphabet_size).
            Each sequence is encoded as a flattened matrix where position i and
            character j are encoded at index (i * alphabet_size + j).
        """
        # Handle pandas DataFrame/Series
        if hasattr(X, "to_numpy"):
            X = X.to_numpy()

        # Flatten to 1D array
        sequences = X.ravel() if isinstance(X, np.ndarray) else X

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

        return encoded

    def get_feature_names_out(self, input_features: list[str]) -> np.ndarray:
        """Get output feature names for transformation.

        Args:
            input_features: Input feature names.

        Returns:
            Array of feature names in the format: column_pos{i}_{char}
        """
        feature_names = []
        for pos in range(self.max_length_):
            for char in self.alphabet_:
                feature_names.append(f"{input_features[0]}_pos{pos}_{char}")

        return np.array(feature_names)


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
        >>> assert X.shape == (2, 20)
        >>> assert y.shape == (2,)
    """

    def __init__(
        self,
        sequence_column: str,
        target_columns: list[str],
        categorical_columns: list[str] = None,
        numerical_columns: list[str] = None,
    ) -> None:
        """Initialize the AssayTransformer.

        Args:
            sequence_column: Name of the column containing biological sequences.
            target_columns: Names of target columns to extract as y.
            categorical_columns: Names of categorical variable columns
                to one-hot encode.
            numerical_columns: Names of numerical variable columns
                to standardize.
        """
        self.sequence_column = sequence_column
        self.target_columns = target_columns
        self.categorical_columns = categorical_columns
        self.numerical_columns = numerical_columns
        self.column_transformer_: ColumnTransformer | None = None
        self.feature_names_: list[str] = []

    def fit(self, X: pl.DataFrame) -> AssayTransformer:
        """Fit the transformer on the training data.

        Args:
            X: Input dataframe containing sequences, variables, and targets.

        Returns:
            Fitted transformer.
        """
        transformers: list[tuple[str, BaseEstimator | str, list[str]]] = []

        transformers.append(
            (self.sequence_column, SequenceOneHotEncoder(), [self.sequence_column])
        )

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

    def transform(self, X: pl.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        """Transform the dataframe to feature matrix X and target vector y.

        Args:
            X: Input dataframe containing sequences, variables, and targets.

        Returns:
            Tuple of (X, y) where:
            - X is the transformed feature matrix of shape (n_samples, n_features)
            - y is the target vector/matrix of shape (n_samples,)
                or (n_samples, n_targets)
        """
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
