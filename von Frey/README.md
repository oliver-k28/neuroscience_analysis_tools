# Von Frey Dixon Cleaner Streamlit App

This Streamlit app cleans raw von Frey up-down data and calculates the **50% withdrawal threshold** for each row using the **Dixon up-down method**.

## Files in this folder

- `app.py` -> the Streamlit app
- `k_table.csv` -> the Dixon lookup table used by the app
- `requirements.txt` -> packages needed for Streamlit Cloud

## Expected input columns

Your uploaded spreadsheet should contain:

- `UpDownPattern`
- `FinalFilament_g (Xf)`

Other columns are preserved and passed through unchanged.

## Output columns added by the app

- `CleanedSequence`
- `k`
- `Threshold_50pct_g`
- `Status`

## Status values

- `ok` -> normal Dixon calculation completed
- `censored_high` -> all O responses, threshold set to 2.0 g
- `censored_low` -> all X responses, threshold set to 0.01 g
- `k_not_found` -> sequence not found in the k table
- `invalid_sequence` -> pattern column was blank or could not be interpreted
- `invalid_xf` -> final filament value was missing or invalid

## Local testing

From this folder, run:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud deployment

1. Push this folder into your GitHub repo.
2. In Streamlit Community Cloud, create a new app from that repo.
3. Set the main file path to `von_frey/app.py` if you place this folder inside a repo folder named `von_frey`.
4. Deploy.
