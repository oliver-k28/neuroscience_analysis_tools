import streamlit as st
import pandas as pd
from io import BytesIO

st.title("Hargreaves Data Cleaner")

# Column names
COL_MOUSE = 'MouseID'
COL_SEX = 'Sex'
COL_DATE = 'Date'
COL_SESSION = 'Session'
COL_PAW = 'Paw'
COL_LATENCY = 'Latency_s'
GROUP_KEYS = [COL_MOUSE, COL_SEX, COL_DATE, COL_SESSION, COL_PAW]


def clean_hargreaves(
    df: pd.DataFrame,
    group_keys=None,
    col_latency: str = 'Latency_s',
):
    if group_keys is None:
        raise ValueError('group_keys must be provided')

    required = set(group_keys + [col_latency])
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}\n"
            f"Found columns: {list(df.columns)}"
        )

    # Make sure latency is numeric
    df = df.copy()
    df[col_latency] = pd.to_numeric(df[col_latency], errors='coerce')
    df = df.dropna(subset=[col_latency]).copy()

    cleaned = (
        df.groupby(group_keys, as_index=False)
          .agg(
              Average_Withdrawal_Latency_s=(col_latency, 'mean'),
              N_trials=(col_latency, 'size'),
          )
    )

    cleaned['Trial_Count_Flag'] = cleaned['N_trials'].apply(
        lambda n: '' if n == 2 else f'CHECK: {n} trials'
    )

    return cleaned


uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    st.subheader("Raw data preview")
    st.dataframe(df.head())

    try:
        cleaned_df = clean_hargreaves(
            df=df,
            group_keys=GROUP_KEYS,
            col_latency=COL_LATENCY,
        )

        st.subheader("Cleaned data preview")
        st.dataframe(cleaned_df.head(20))

        output = BytesIO()
        cleaned_df.to_excel(output, index=False, engine="openpyxl")
        output.seek(0)

        st.download_button(
            "Download cleaned Excel file",
            data=output,
            file_name="cleaned_hargreaves.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(str(e))
