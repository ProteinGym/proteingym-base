import io
import pandas as pd
from sklearn.model_selection import train_test_split
from pg2_dataset.datasets.dataset import Dataset
from pg2_dataset.io.bytes import read_bytes


class CSVDataset(Dataset):
    def __init__(
        self,
        file_path: str,
        random_state: int,
        train_size: int | float,
        test_size: int | float,
        index_col: int | None = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        data_str = read_bytes(file_path).decode("utf-8")

        df = pd.read_csv(io.StringIO(data_str), index_col=index_col)

        train, test = train_test_split(
            df, random_state=random_state, train_size=train_size, test_size=test_size
        )

        self._train = train.to_dict(orient="records")
        self._test = test.to_dict(orient="records")
