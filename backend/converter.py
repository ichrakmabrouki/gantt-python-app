import re
import pandas as pd

def convert_txt_to_df(file_content: str) -> pd.DataFrame:
    """Parse mchs_CP.txt → DataFrame opérations"""
    rows = []
    pattern = re.compile(
        r'<"modes\[<(\d+),(\d+),(\d+)>\]"\s+'
        r'(\d+)\s+(\d+)\s+(\d+)\s+'
        r'(\d+)\s+(\d+)\s+(\d+)>'
    )
    blocs = re.findall(r'\{([^}]*)\}', file_content)
    for bloc in blocs:
        for match in pattern.finditer(bloc):
            (op_id, mach_id, proc_time,
             mach_seq, glob_seq, mach_seq2,
             start, end, duration) = match.groups()
            rows.append({
                "OperationID":    int(op_id),
                "MachineID":      int(mach_id),
                "MachineLabel":   f"Machine {mach_id}",
                "ProcessingTime": int(proc_time),
                "StartTime":      int(start),
                "EndTime":        int(end),
                "Duration":       int(duration)
            })
    return pd.DataFrame(rows)


def load_jobs_from_txt(file_content: str) -> pd.DataFrame:
    """Parse opts.txt → DataFrame OperationID / JobID"""
    rows = []
    for line in file_content.splitlines():
        match = re.search(r'<(\d+),(\d+),(\d+)>', line)
        if match:
            rows.append({
                "OperationID":    int(match.group(1)),
                "JobID":          int(match.group(2)),
                "OperationOrder": int(match.group(3))
            })
    return pd.DataFrame(rows)