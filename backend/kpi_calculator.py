import pandas as pd

def compute_kpis(df: pd.DataFrame, prix: dict) -> pd.DataFrame:
    """prix = {job_id (int): prix_par_minute (float)}"""
    df = df.copy()
    df["Prix_Unitaire"] = df["JobID"].map(prix).fillna(0)
    df["Profit"]        = df["Duration"] * df["Prix_Unitaire"]
    return df

def summary_by_machine(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    if "MachineLabel" not in work.columns:
        raise KeyError("MachineLabel")
    if "OperationID" not in work.columns:
        work["OperationID"] = range(1, len(work) + 1)
    if "Duration" not in work.columns:
        if "Duree_min" in work.columns:
            work["Duration"] = work["Duree_min"]
        else:
            work["Duration"] = 0
    if "Profit" not in work.columns:
        if "Profit (€)" in work.columns:
            work["Profit"] = work["Profit (€)"]
        else:
            work["Profit"] = 0

    return work.groupby("MachineLabel").agg(
        Nb_Operations=("OperationID", "count"),
        Charge_min=("Duration", "sum"),
        Profit_total=("Profit", "sum")
    ).reset_index()

def summary_by_job(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    if "JobLabel" not in work.columns:
        raise KeyError("JobLabel")
    if "OperationID" not in work.columns:
        work["OperationID"] = 1
    if "Duration" not in work.columns:
        if "Duree_min" in work.columns:
            work["Duration"] = work["Duree_min"]
        else:
            work["Duration"] = 0
    if "Profit" not in work.columns:
        if "Profit (€)" in work.columns:
            work["Profit"] = work["Profit (€)"]
        else:
            work["Profit"] = 0

    return work.groupby("JobLabel").agg(
        Nb_Operations=("OperationID", "count"),
        Duree_totale=("Duration", "sum"),
        Profit_total=("Profit", "sum")
    ).reset_index()
