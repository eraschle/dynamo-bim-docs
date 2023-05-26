from pathlib import Path
from typing import Dict, cast

import pandas as pd

EXCEL_EXTENSIONS = [".xlsx", ".xls"]


def is_excel_extension(extension: str):
    return extension in EXCEL_EXTENSIONS


def read(path: Path, **kwargs) -> Dict[str, pd.DataFrame]:
    if not is_excel_extension(path.suffix):
        raise ValueError(f"{path.name} is a unknown Excel extension.")
    options = {
        "sheet_name": None,
        "parse_dates": False,
        "keep_default_na": False
    }
    options.update(kwargs)
    import_data = pd.read_excel(path.absolute(), **options)

    excel_data = {}
    for sheet, data in import_data.items():
        data = data.rename(str, axis='columns')
        data = data.rename(str.strip, axis='columns')
        excel_data[cast(str, sheet)] = data
    return excel_data
