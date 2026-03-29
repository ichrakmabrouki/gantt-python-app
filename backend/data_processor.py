
import pandas as pd

REQUIRED_COLUMNS = ["OperationID", "MachineID", "StartTime", "EndTime"]

def load_file(uploaded_file) -> pd.DataFrame:
    if uploaded_file.name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)
    return pd.read_csv(uploaded_file)

def validate(df: pd.DataFrame) -> tuple[bool, str]:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return False, f"Colonnes manquantes : {', '.join(missing)}"
    return True, "OK"

def parse_and_clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["MachineLabel"] = "Machine " + df["MachineID"].astype(str)
    df["Duration"]     = df["EndTime"] - df["StartTime"]
    return df

def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")