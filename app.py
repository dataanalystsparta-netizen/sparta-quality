import streamlit as st
import pandas as pd


# ==========================================================
# PAGE CONFIG
# ==========================================================

st.set_page_config(
    page_title="Sparta QA Checker",
    page_icon="✅",
    layout="wide"
)


# ==========================================================
# FIXED FILE STRUCTURE
# ==========================================================

# The uploaded file has NO headers.
# These names correspond to the fixed column positions.

COLUMN_NAMES = [
    "Serial_No",                 # 1
    "Month",                     # 2
    "Agent",                     # 3
    "Verifier",                  # 4
    "Company",                   # 5
    "Sale_Date",                 # 6
    "Raw_7",                     # 7
    "Raw_8",                     # 8
    "Customer_Name",             # 9
    "Phone",                     # 10
    "Raw_11",                    # 11
    "Raw_12",                    # 12
    "Raw_13",                    # 13
    "Raw_14",                    # 14
    "Raw_15",                    # 15
    "Raw_16",                    # 16
    "Raw_17",                    # 17
    "Confirmation",              # 18
    "Date_of_Birth",             # 19
    "Current_Provider",          # 20
    "Customer_Address",          # 21
    "Bank_Name",                 # 22
    "Raw_23",                    # 23
    "Raw_24",                    # 24
    "Raw_25",                    # 25
    "Package_Offered",           # 26
    "Service",                   # 27
    "Raw_28",                    # 28
    "Broadband_Type",             # 29
    "Router_Charges",            # 30
    "Raw_31",                    # 31
    "Raw_32",                    # 32
    "Payment_Frequency",         # 33
    "Payment_Method",             # 34
    "Contract_Duration",          # 35
    "Calling_Package",            # 36
    "Raw_37",                    # 37
    "Enrollment_Fee",             # 38
    "Additional_Notes",           # 39
    "Lead_Source"                 # 40
]


# ==========================================================
# HEADER / TITLE
# ==========================================================

st.title("Sparta QA Checker")

st.caption("Upload the daily sales file to begin quality checking.")


# ==========================================================
# FILE UPLOAD
# ==========================================================

uploaded_file = st.file_uploader(
    "Upload Daily Sales Excel File",
    type=["xlsx", "xls"]
)


# ==========================================================
# PROCESS FILE
# ==========================================================

if uploaded_file is not None:

    try:

        # Read file WITHOUT assuming headers
        df = pd.read_excel(
            uploaded_file,
            header=None
        )

        # --------------------------------------------------
        # Validate number of columns
        # --------------------------------------------------

        expected_columns = len(COLUMN_NAMES)
        actual_columns = df.shape[1]

        if actual_columns != expected_columns:

            st.error(
                f"Unexpected file structure. "
                f"Expected {expected_columns} columns, "
                f"but found {actual_columns} columns."
            )

            st.stop()

        # --------------------------------------------------
        # Apply our internal column names
        # --------------------------------------------------

        df.columns = COLUMN_NAMES

        # --------------------------------------------------
        # Add QA status
        # --------------------------------------------------

        df["QA_Status"] = "Quality Pending"

        # --------------------------------------------------
        # Create internal record ID
        # --------------------------------------------------

        df["QA_ID"] = range(1, len(df) + 1)

        # Put QA_ID first
        qa_id = df.pop("QA_ID")
        df.insert(0, "QA_ID", qa_id)

        # Put QA_Status near the front
        qa_status = df.pop("QA_Status")
        df.insert(7, "QA_Status", qa_status)

        # --------------------------------------------------
        # Store data in Streamlit session
        # --------------------------------------------------

        st.session_state["sales_data"] = df

        # --------------------------------------------------
        # Success message
        # --------------------------------------------------

        st.success(
            f"File uploaded successfully — "
            f"{len(df):,} sales loaded."
        )

    except Exception as e:

        st.error("Could not read the uploaded Excel file.")

        st.exception(e)


# ==========================================================
# DISPLAY IMPORTED SALES
# ==========================================================

if "sales_data" in st.session_state:

    df = st.session_state["sales_data"]

    st.divider()

    st.subheader("Sales Loaded for Quality Checking")

    # ------------------------------------------------------
    # Summary
    # ------------------------------------------------------

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Total Sales",
            len(df)
        )

    with col2:
        st.metric(
            "Quality Pending",
            (df["QA_Status"] == "Quality Pending").sum()
        )

    with col3:
        st.metric(
            "QA Completed",
            (df["QA_Status"] == "Completed").sum()
        )

    st.divider()

    # ------------------------------------------------------
    # Filters
    # ------------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:

        agents = ["All"] + sorted(
            df["Agent"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        selected_agent = st.selectbox(
            "Filter by Agent",
            agents
        )

    with col2:

        statuses = ["All"] + sorted(
            df["QA_Status"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        selected_status = st.selectbox(
            "Filter by QA Status",
            statuses
        )

    # ------------------------------------------------------
    # Apply filters
    # ------------------------------------------------------

    display_df = df.copy()

    if selected_agent != "All":
        display_df = display_df[
            display_df["Agent"].astype(str) == selected_agent
        ]

    if selected_status != "All":
        display_df = display_df[
            display_df["QA_Status"].astype(str) == selected_status
        ]

    # ------------------------------------------------------
    # Display useful columns only
    # ------------------------------------------------------

    display_columns = [
        "QA_ID",
        "Serial_No",
        "Sale_Date",
        "Agent",
        "Verifier",
        "Customer_Name",
        "Phone",
        "Current_Provider",
        "Package_Offered",
        "Broadband_Type",
        "Payment_Method",
        "QA_Status"
    ]

    st.dataframe(
        display_df[display_columns],
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        f"Showing {len(display_df):,} of {len(df):,} sales"
    )
