import math
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

STEP_SIZE = 0.25
CENSORED_HIGH_VALUE = 2.0
CENSORED_LOW_VALUE = 0.01
APP_DIR = Path(__file__).resolve().parent
DEFAULT_K_TABLE_PATH = APP_DIR / "k_table.csv"


def load_k_table(k_table_path: Path = DEFAULT_K_TABLE_PATH) -> dict:
    """Load the Dixon k lookup table into a dictionary."""
    k_df = pd.read_csv(k_table_path)
    required = {"sequence", "k"}
    missing = required - set(k_df.columns)
    if missing:
        raise ValueError(f"k_table.csv is missing required columns: {sorted(missing)}")
    return dict(
        zip(
            k_df["sequence"].astype(str).str.strip().str.upper(),
            pd.to_numeric(k_df["k"], errors="coerce"),
        )
    )


def clean_pattern(pattern) -> str:
    """Standardize the up-down response string to O/X only."""
    if pd.isna(pattern):
        return ""
    pattern = str(pattern).upper().replace("0", "O")
    return "".join(ch for ch in pattern if ch in {"O", "X"})


def compute_threshold(pattern, final_filament_g, k_map, d: float = STEP_SIZE):
    """Compute 50% withdrawal threshold using the Dixon up-down method."""
    seq = clean_pattern(pattern)
    xf = pd.to_numeric(pd.Series([final_filament_g]), errors="coerce").iloc[0]

    if not seq:
        return {
            "CleanedSequence": seq,
            "k": None,
            "Threshold_50pct_g": None,
            "Status": "invalid_sequence",
        }

    if pd.isna(xf):
        return {
            "CleanedSequence": seq,
            "k": None,
            "Threshold_50pct_g": None,
            "Status": "invalid_xf",
        }

    unique_chars = set(seq)
    if unique_chars == {"O"}:
        return {
            "CleanedSequence": seq,
            "k": None,
            "Threshold_50pct_g": CENSORED_HIGH_VALUE,
            "Status": "censored_high",
        }
    if unique_chars == {"X"}:
        return {
            "CleanedSequence": seq,
            "k": None,
            "Threshold_50pct_g": CENSORED_LOW_VALUE,
            "Status": "censored_low",
        }

    k = k_map.get(seq)
    if k is None or pd.isna(k):
        return {
            "CleanedSequence": seq,
            "k": None,
            "Threshold_50pct_g": None,
            "Status": "k_not_found",
        }

    threshold = float(xf) * (10 ** (float(k) * d))
    return {
        "CleanedSequence": seq,
        "k": float(k),
        "Threshold_50pct_g": threshold,
        "Status": "ok",
    }


def find_column(columns, candidates):
    lower_map = {str(col).strip().lower(): col for col in columns}
    for candidate in candidates:
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]

    for col in columns:
        col_lower = str(col).strip().lower()
        if all(token in col_lower for token in candidates[0].lower().split()):
            return col
    return None


def process_von_frey_dataframe(df: pd.DataFrame, k_map: dict) -> pd.DataFrame:
    """Add Dixon-derived 50% threshold columns to every input row."""
    pattern_col = None
    xf_col = None

    for col in df.columns:
        col_lower = str(col).strip().lower()
        if pattern_col is None and "pattern" in col_lower:
            pattern_col = col
        if xf_col is None and ("finalfilament" in col_lower or ("final" in col_lower and "xf" in col_lower) or col_lower == "xf"):
            xf_col = col

    if pattern_col is None:
        raise ValueError("Could not find the UpDownPattern column.")
    if xf_col is None:
        raise ValueError("Could not find the FinalFilament_g (Xf) column.")

    results = df.apply(
        lambda row: compute_threshold(row[pattern_col], row[xf_col], k_map),
        axis=1,
        result_type="expand",
    )

    output_df = df.copy()
    insert_cols = ["CleanedSequence", "k", "Threshold_50pct_g", "Status"]
    for col in insert_cols:
        output_df[col] = results[col]
    return output_df


def dataframe_to_excel_bytes(df: pd.DataFrame) -> bytes:
    """Export a dataframe to an in-memory Excel file."""
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="cleaned_von_frey")
    bio.seek(0)
    return bio.getvalue()


def main():
    st.set_page_config(page_title="Von Frey Dixon Cleaner", page_icon="🧪", layout="centered")

    st.title("Von Frey Dixon Cleaner")
    st.write(
        "Upload your raw von Frey spreadsheet and this app will calculate the 50% withdrawal threshold "
        "for each row using the Dixon up-down method."
    )

    with st.expander("What this app expects"):
        st.markdown(
            """
            - A spreadsheet file in **.xlsx**, **.xls**, or **.csv** format
            - A response-pattern column such as **UpDownPattern**
            - A final-filament column such as **FinalFilament_g (Xf)**

            **Outputs added to your file**
            - `CleanedSequence`
            - `k`
            - `Threshold_50pct_g`
            - `Status`
            """
        )

    uploaded_file = st.file_uploader("Upload raw von Frey data", type=["xlsx", "xls", "csv"])

    if uploaded_file is None:
        st.stop()

    try:
        if uploaded_file.name.lower().endswith(".csv"):
            raw_df = pd.read_csv(uploaded_file)
        else:
            raw_df = pd.read_excel(uploaded_file)

        k_map = load_k_table()
        cleaned_df = process_von_frey_dataframe(raw_df, k_map)
    except Exception as exc:
        st.error(f"Something went wrong while processing the file: {exc}")
        st.stop()

    st.success("File processed successfully.")

    st.subheader("Preview")
    st.dataframe(cleaned_df.head(20), use_container_width=True)

    st.subheader("Status summary")
    status_counts = cleaned_df["Status"].value_counts(dropna=False).rename_axis("Status").reset_index(name="Count")
    st.dataframe(status_counts, use_container_width=True, hide_index=True)

    if (cleaned_df["Status"] == "k_not_found").any():
        missing_df = cleaned_df.loc[cleaned_df["Status"] == "k_not_found"]
        st.warning(
            f"{len(missing_df)} row(s) had sequences that were not found in k_table.csv. "
            "Those rows were left blank for Threshold_50pct_g."
        )
        st.dataframe(missing_df.head(20), use_container_width=True)

    output_bytes = dataframe_to_excel_bytes(cleaned_df)
    output_name = f"{Path(uploaded_file.name).stem}_cleaned.xlsx"

    st.download_button(
        label="Download cleaned file",
        data=output_bytes,
        file_name=output_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    main()
