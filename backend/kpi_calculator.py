import pandas as pd

def compute_kpis(df: pd.DataFrame, prix: dict) -> pd.DataFrame:
    """prix = {job_id (int): prix_par_minute (float)}"""
    df = df.copy()
    df["Prix_Unitaire"] = df["JobID"].map(prix).fillna(0)
    df["Profit"]        = df["Duration"] * df["Prix_Unitaire"]
    return df

def summary_by_machine(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby("MachineLabel").agg(
        Nb_Operations = ("OperationID", "count"),
        Charge_min    = ("Duration", "sum"),
        Profit_total  = ("Profit", "sum")
    ).reset_index()

def summary_by_job(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby("JobLabel").agg(
        Nb_Operations  = ("OperationID", "count"),
        Duree_totale   = ("Duration", "sum"),
        Profit_total   = ("Profit", "sum")
    ).reset_index()