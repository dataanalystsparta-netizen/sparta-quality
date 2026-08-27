import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials


# ==========================================================
# PAGE CONFIG
# ==========================================================

st.set_page_config(
    page_title="Sparta QA Checker",
    page_icon="✅",
    layout="wide"
)


# ==========================================================
# CONFIG
# ==========================================================

GOOGLE_SHEET_ID = "YOUR_GOOGLE_SHEET_ID"
SHEET_NAME = "Sheet1"


# ==========================================================
# GOOGLE SHEETS CONNECTION
# ==========================================================

@st.cache_data(ttl=300)
def load_google_sheet():

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly"
    ]

    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )

    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)

    worksheet = spreadsheet.worksheet(SHEET_NAME)

    data = worksheet.get_all_records()

    return pd.DataFrame(data)


# ==========================================================
# APP
# ==========================================================

st.title("Sparta QA Checker")

st.caption("Step 2 — Google Sheet connection")


# ==========================================================
# LOAD DATA
# ==========================================================

try:

    df = load_google_sheet()

    st.success(
        f"Google Sheet connected successfully — {len(df):,} records loaded."
    )

    st.subheader("Sales Data")

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )

except Exception as e:

    st.error("Could not connect to the Google Sheet.")

    st.code(str(e))
