import streamlit as st
import pandas as pd
from io import BytesIO


# ==========================================================
# PAGE CONFIG
# ==========================================================

st.set_page_config(
    page_title="Sparta QA Checker",
    page_icon="✅",
    layout="wide"
)


# ==========================================================
# FIXED 40-COLUMN FILE STRUCTURE
# ==========================================================

COLUMN_NAMES = [
    "Serial_No",             # 1
    "Month",                 # 2
    "Agent",                 # 3
    "Verifier",              # 4
    "Company",               # 5
    "Sale_Date",             # 6
    "Raw_7",                 # 7
    "Raw_8",                 # 8
    "Customer_Name",         # 9
    "Phone",                 # 10
    "Raw_11",                # 11
    "Raw_12",                # 12
    "Raw_13",                # 13
    "Raw_14",                # 14
    "Raw_15",                # 15
    "Raw_16",                # 16
    "Raw_17",                # 17
    "Confirmation",          # 18
    "Date_of_Birth",         # 19
    "Current_Provider",      # 20
    "Customer_Address",      # 21
    "Bank_Name",             # 22
    "Raw_23",                # 23
    "Raw_24",                # 24
    "Raw_25",                # 25
    "Package_Offered",       # 26
    "Service",               # 27
    "Raw_28",                # 28
    "Broadband_Type",        # 29
    "Router_Charges",        # 30
    "Raw_31",                # 31
    "Raw_32",                # 32
    "Payment_Frequency",     # 33
    "Payment_Method",        # 34
    "Contract_Duration",     # 35
    "Calling_Feature",       # 36
    "Raw_37",                # 37
    "Bill_Cost",             # 38
    "Additional_Notes",      # 39
    "Lead_Source"            # 40
]

EXPECTED_COLUMN_COUNT = 40


# ==========================================================
# FINAL QA RESULTS
# ==========================================================

FINAL_RESULTS = [
    "Approved",
    "Rejected",
    "Cancelled",
    "Reworked Required",
    "Hold"
]


# ==========================================================
# QA QUESTIONS
# ==========================================================

QA_QUESTIONS = [
    "Did the agent greet the customer and introduce themselves and the company properly?",

    "Did the agent clearly inform the purpose of the call in a professional and customer-centric manner?",

    'Did the agent avoid inappropriate opening remarks (e.g., referring to the customer as "retired or pensioner")?',

    "Did the agent confirm the customer’s current service provider and type of line (e.g., copper/fiber)?",

    "Did the agent ask about the customer’s current usage or bill amount to tailor their offer?",

    "Did the agent confirm if the customer is under contract with their current provider?",

    "Did the agent ask about any additional services, for example extension lines, cordless phones, TV, BB and type of BB services (if applicable)?",

    "Did the agent appropriately compare Sparta Telecom's offerings with the customer’s current provider's pricing/services?",

    "Did the agent verify the customer’s awareness of their current service details (e.g., bills, provider name)?",

    "Did the agent confirm today's date or check for signs of vulnerability (e.g., customer being unclear or confused)?",

    "Did the agent effectively engage the customer by asking personalized questions (rapport building)?",

    "Did the agent explain savings AND quick support services etc. in a way that aligned with the customer's situation?",

    "Did the agent offer an appropriate package based on the customer’s usage and preferences?",

    "Did the agent explain VAT, call setup fees, and any other charges clearly?",

    "Did the agent mention the 24-month price guarantee or any other relevant contract terms?",

    "Did the agent clarify that Sparta Telecom is a separate company to avoid confusion?",

    "Did the agent collect all necessary details (e.g., Name, DOB, address, email, alternate contact) accurately?",

    "Did the agent confirm the customer’s payment mode and attempt to collect direct debit details professionally?",

    "Did the agent verify the decision-maker or presence of family interference (if applicable)?",

    "Did the agent refrain from mentioning the cooling-off period and customer rights without being asked?",

    "Did the agent disclose router charges, line import charges, or broadband downgrade/removal charges if applicable?",

    "Did the agent explain any health alarm systems, itemized billing, or calling features if relevant to the package?",

    "Did the agent avoid pressuring, compelling, or misleading the customer into agreeing to the sale?",

    "Did the agent confirm that the customer is happy and satisfied with the package being offered?",

    "Did the agent ensure there was no confusion about proceeding with the package/sale?",

    "Did the verifier perform the script verbatim and follow compliance guidelines?",

    "Did the verifier ensure all customer details and payment details were accurate and matched the recorded sale?",

    "Did the verifier confirm that the sale was properly explained and not based solely on paperwork?"
]


# ==========================================================
# FATAL PARAMETERS
# ==========================================================

# Add parameter numbers here when finalized.
#
# Example:
# FATAL_PARAMETERS = {23, 27}

FATAL_PARAMETERS = set()


# ==========================================================
# SAFE VALUE HELPER
# ==========================================================

def safe_value(row, column_name):
    """
    Safely retrieve a value from a row.

    Prevents the application from crashing if a column
    is missing or contains NaN.
    """

    if column_name not in row.index:
        return ""

    value = row[column_name]

    if pd.isna(value):
        return ""

    return str(value).strip()


# ==========================================================
# SCORING
# ==========================================================

def calculate_score(answers):
    """
    Yes = full credit
    No = zero credit
    N/A = excluded
    """

    applicable = [
        answer
        for answer in answers.values()
        if answer in ["Yes", "No"]
    ]

    if not applicable:
        return 0.0

    yes_count = sum(
        1
        for answer in applicable
        if answer == "Yes"
    )

    return round(
        (yes_count / len(applicable)) * 100,
        2
    )


def has_fatal_failure(answers):

    for parameter_id in FATAL_PARAMETERS:

        if answers.get(parameter_id) == "No":
            return True

    return False


# ==========================================================
# SALE LABEL
# ==========================================================

def sale_label(df, qa_id):

    matching = df[
        df["QA_ID"] == qa_id
    ]

    if matching.empty:
        return f"QA #{qa_id}"

    row = matching.iloc[0]

    customer = safe_value(
        row,
        "Customer_Name"
    )

    agent = safe_value(
        row,
        "Agent"
    )

    status = safe_value(
        row,
        "QA_Status"
    )

    return (
        f"QA #{qa_id} — "
        f"{customer} — "
        f"Agent: {agent} — "
        f"{status}"
    )


# ==========================================================
# EXCEL EXPORT
# ==========================================================

def create_excel_download(df, qa_answers):

    output = BytesIO()

    # ------------------------------------------------------
    # QA Results sheet
    # ------------------------------------------------------

    result_columns = [
        "QA_ID",
        "Sale_Date",
        "Agent",
        "Verifier",
        "Customer_Name",
        "Phone",
        "QA_Status",
        "QA_Score",
        "Fatal_Failure",
        "Final_QA_Result",
        "QA_Comments"
    ]

    # Only use columns that actually exist
    available_result_columns = [
        column
        for column in result_columns
        if column in df.columns
    ]

    results_df = df[
        available_result_columns
    ].copy()

    # ------------------------------------------------------
    # Detailed QA sheet
    # ------------------------------------------------------

    detailed_rows = []

    for _, row in df.iterrows():

        qa_id = row["QA_ID"]

        answers = qa_answers.get(
            qa_id,
            {}
        )

        detailed_row = {
            "QA_ID": qa_id,
            "Sale_Date": safe_value(row, "Sale_Date"),
            "Agent": safe_value(row, "Agent"),
            "Verifier": safe_value(row, "Verifier"),
            "Customer_Name": safe_value(row, "Customer_Name"),
            "Phone": safe_value(row, "Phone"),
            "QA_Status": safe_value(row, "QA_Status"),
            "QA_Score": row.get("QA_Score", ""),
            "Fatal_Failure": row.get("Fatal_Failure", ""),
            "Final_QA_Result": safe_value(
                row,
                "Final_QA_Result"
            ),
            "QA_Comments": safe_value(
                row,
                "QA_Comments"
            )
        }

        # Add all 28 parameters
        for parameter_id in range(1, 29):

            detailed_row[
                f"Parameter_{parameter_id}"
            ] = answers.get(
                parameter_id,
                "Yes"
            )

        detailed_rows.append(
            detailed_row
        )

    detailed_df = pd.DataFrame(
        detailed_rows
    )

    # ------------------------------------------------------
    # Write Excel
    # ------------------------------------------------------

    with pd.ExcelWriter(
        output,
        engine="xlsxwriter"
    ) as writer:

        # Sheet 1
        results_df.to_excel(
            writer,
            sheet_name="QA Results",
            index=False
        )

        # Sheet 2
        detailed_df.to_excel(
            writer,
            sheet_name="Detailed QA",
            index=False
        )

        workbook = writer.book

        header_format = workbook.add_format({
            "bold": True,
            "text_wrap": True,
            "valign": "top"
        })

        # --------------------------------------------------
        # Format sheets
        # --------------------------------------------------

        for sheet_name, dataframe in [
            ("QA Results", results_df),
            ("Detailed QA", detailed_df)
        ]:

            worksheet = writer.sheets[
                sheet_name
            ]

            # Headers
            for col_num, column_name in enumerate(
                dataframe.columns
            ):

                worksheet.write(
                    0,
                    col_num,
                    column_name,
                    header_format
                )

            # Freeze top row
            worksheet.freeze_panes(
                1,
                0
            )

            # Autofilter
            if not dataframe.empty:

                worksheet.autofilter(
                    0,
                    0,
                    len(dataframe),
                    len(dataframe.columns) - 1
                )

            # Widths
            for col_num, column_name in enumerate(
                dataframe.columns
            ):

                if column_name.startswith(
                    "Parameter_"
                ):

                    width = 15

                elif column_name in [
                    "Customer_Name",
                    "QA_Comments"
                ]:

                    width = 32

                elif column_name == "Phone":

                    width = 16

                else:

                    width = 18

                worksheet.set_column(
                    col_num,
                    col_num,
                    width
                )

    output.seek(0)

    return output


# ==========================================================
# SESSION STATE
# ==========================================================

if "qa_answers" not in st.session_state:

    st.session_state[
        "qa_answers"
    ] = {}


# ==========================================================
# HEADER
# ==========================================================

st.title("Sparta QA Checker")

st.caption(
    "Upload sales → complete QA → save progress → submit final result."
)


# ==========================================================
# FILE UPLOAD
# ==========================================================

uploaded_file = st.file_uploader(
    "Upload Daily Sales Excel File",
    type=["xlsx", "xls"]
)


# ==========================================================
# PROCESS UPLOAD
# ==========================================================

if uploaded_file is not None:

    try:

        # --------------------------------------------------
        # Read raw Excel
        # --------------------------------------------------

        df = pd.read_excel(
            uploaded_file,
            header=None
        )

        # --------------------------------------------------
        # Validate column count
        # --------------------------------------------------

        actual_columns = df.shape[1]

        if actual_columns != EXPECTED_COLUMN_COUNT:

            st.error(
                f"Unexpected file structure. "
                f"Expected exactly {EXPECTED_COLUMN_COUNT} "
                f"columns, but found {actual_columns}."
            )

            st.stop()

        # --------------------------------------------------
        # Apply fixed names
        # --------------------------------------------------

        df.columns = COLUMN_NAMES

        # --------------------------------------------------
        # Remove completely blank rows
        # --------------------------------------------------

        df = df.dropna(
            how="all"
        ).reset_index(drop=True)

        # --------------------------------------------------
        # Create unique upload key
        # --------------------------------------------------

        uploaded_file_key = (
            uploaded_file.name
            + "_"
            + str(len(df))
        )

        # --------------------------------------------------
        # New upload
        # --------------------------------------------------

        if st.session_state.get(
            "uploaded_file_key"
        ) != uploaded_file_key:

            # QA ID
            df["QA_ID"] = range(
                1,
                len(df) + 1
            )

            # QA fields
            df["QA_Status"] = (
                "Quality Pending"
            )

            df["QA_Score"] = None

            df["Fatal_Failure"] = False

            df["Final_QA_Result"] = ""

            df["QA_Comments"] = ""

            # Store
            st.session_state[
                "sales_data"
            ] = df

            st.session_state[
                "uploaded_file_key"
            ] = uploaded_file_key

            # Reset answers
            st.session_state[
                "qa_answers"
            ] = {}

            st.success(
                f"File uploaded successfully — "
                f"{len(df):,} sales loaded."
            )

    except Exception as e:

        st.error(
            "Could not read the uploaded Excel file."
        )

        st.exception(e)


# ==========================================================
# MAIN APP
# ==========================================================

if "sales_data" in st.session_state:

    df = st.session_state[
        "sales_data"
    ]

    # ======================================================
    # DASHBOARD
    # ======================================================

    st.divider()

    st.subheader(
        "QA Dashboard"
    )

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:

        st.metric(
            "Total Sales",
            len(df)
        )

    with col2:

        st.metric(
            "Pending",
            int(
                (
                    df["QA_Status"]
                    == "Quality Pending"
                ).sum()
            )
        )

    with col3:

        st.metric(
            "Completed",
            int(
                (
                    df["QA_Status"]
                    == "Completed"
                ).sum()
            )
        )

    with col4:

        st.metric(
            "Approved",
            int(
                (
                    df["Final_QA_Result"]
                    == "Approved"
                ).sum()
            )
        )

    with col5:

        st.metric(
            "Rejected",
            int(
                (
                    df["Final_QA_Result"]
                    == "Rejected"
                ).sum()
            )
        )

    # ======================================================
    # FILTERS
    # ======================================================

    st.divider()

    st.subheader(
        "Find Sale"
    )

    col1, col2, col3 = st.columns(3)

    # ------------------------------------------------------
    # Agent
    # ------------------------------------------------------

    with col1:

        agents = ["All"] + sorted(
            df["Agent"]
            .fillna("")
            .astype(str)
            .unique()
            .tolist()
        )

        selected_agent = st.selectbox(
            "Agent",
            agents
        )

    filtered_df = df.copy()

    if selected_agent != "All":

        filtered_df = filtered_df[
            filtered_df["Agent"]
            .astype(str)
            == selected_agent
        ]

    # ------------------------------------------------------
    # QA Status
    # ------------------------------------------------------

    with col2:

        statuses = [
            "All",
            "Quality Pending",
            "Completed"
        ]

        selected_status = st.selectbox(
            "QA Status",
            statuses
        )

    if selected_status != "All":

        filtered_df = filtered_df[
            filtered_df["QA_Status"]
            == selected_status
        ]

    # ------------------------------------------------------
    # Final Result
    # ------------------------------------------------------

    with col3:

        selected_result = st.selectbox(
            "Final Result",
            ["All"] + FINAL_RESULTS
        )

    if selected_result != "All":

        filtered_df = filtered_df[
            filtered_df["Final_QA_Result"]
            == selected_result
        ]

    # ======================================================
    # SALE SELECTION
    # ======================================================

    st.divider()

    st.subheader(
        "Select Sale for Quality Check"
    )

    if filtered_df.empty:

        st.warning(
            "No sales match the selected filters."
        )

    else:

        sale_options = filtered_df[
            "QA_ID"
        ].tolist()

        selected_qa_id = st.selectbox(
            "Sale",
            sale_options,
            format_func=lambda x: sale_label(
                df,
                x
            )
        )

        # ==================================================
        # SELECTED SALE
        # ==================================================

        selected_rows = df[
            df["QA_ID"]
            == selected_qa_id
        ]

        if selected_rows.empty:

            st.error(
                "Selected sale could not be found."
            )

            st.stop()

        sale = selected_rows.iloc[0]

        # ==================================================
        # SALE DETAILS
        # ==================================================

        st.divider()

        st.subheader(
            "Sale Details"
        )

        # --------------------------------------------------
        # Row 1
        # --------------------------------------------------

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            st.caption(
                "Customer"
            )

            st.write(
                safe_value(
                    sale,
                    "Customer_Name"
                )
            )

        with col2:

            st.caption(
                "Phone"
            )

            st.write(
                safe_value(
                    sale,
                    "Phone"
                )
            )

        with col3:

            st.caption(
                "Agent"
            )

            st.write(
                safe_value(
                    sale,
                    "Agent"
                )
            )

        with col4:

            st.caption(
                "Verifier"
            )

            st.write(
                safe_value(
                    sale,
                    "Verifier"
                )
            )

        # --------------------------------------------------
        # Row 2
        # --------------------------------------------------

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            st.caption(
                "Sale Date"
            )

            st.write(
                safe_value(
                    sale,
                    "Sale_Date"
                )
            )

        with col2:

            st.caption(
                "Current Provider"
            )

            st.write(
                safe_value(
                    sale,
                    "Current_Provider"
                )
            )

        with col3:

            st.caption(
                "Broadband Type"
            )

            st.write(
                safe_value(
                    sale,
                    "Broadband_Type"
                )
            )

        with col4:

            st.caption(
                "Payment Method"
            )

            st.write(
                safe_value(
                    sale,
                    "Payment_Method"
                )
            )

        # --------------------------------------------------
        # Row 3
        # --------------------------------------------------

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            st.caption(
                "Package"
            )

            st.write(
                safe_value(
                    sale,
                    "Package_Offered"
                )
            )

        with col2:

            st.caption(
                "Service"
            )

            st.write(
                safe_value(
                    sale,
                    "Service"
                )
            )

        with col3:

            st.caption(
                "Router Charges"
            )

            st.write(
                safe_value(
                    sale,
                    "Router_Charges"
                )
            )

        with col4:

            st.caption(
                "Contract Duration"
            )

            st.write(
                safe_value(
                    sale,
                    "Contract_Duration"
                )
            )

        # --------------------------------------------------
        # Row 4
        # --------------------------------------------------

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            st.caption(
                "1471 / 1571"
            )

            st.write(
                safe_value(
                    sale,
                    "Calling_Feature"
                )
            )

        with col2:

            st.caption(
                "Bill / Cost"
            )

            st.write(
                safe_value(
                    sale,
                    "Bill_Cost"
                )
            )

        with col3:

            st.caption(
                "Payment Frequency"
            )

            st.write(
                safe_value(
                    sale,
                    "Payment_Frequency"
                )
            )

        with col4:

            st.caption(
                "Lead Source"
            )

            st.write(
                safe_value(
                    sale,
                    "Lead_Source"
                )
            )

        # --------------------------------------------------
        # Address
        # --------------------------------------------------

        st.caption(
            "Customer Address"
        )

        st.write(
            safe_value(
                sale,
                "Customer_Address"
            )
        )

        # --------------------------------------------------
        # Additional Notes
        # --------------------------------------------------

        notes = safe_value(
            sale,
            "Additional_Notes"
        )

        if notes and notes.lower() != "n/a":

            st.caption(
                "Additional Sale Notes"
            )

            st.info(
                notes
            )

        # ==================================================
        # EXISTING ANSWERS
        # ==================================================

        current_answers = (
            st.session_state[
                "qa_answers"
            ].get(
                selected_qa_id,
                {}
            )
        )

        # ==================================================
        # QA CHECKLIST
        # ==================================================

        st.divider()

        st.subheader(
            "Quality Checklist"
        )

        st.info(
            "All questions default to Yes. "
            "Change any question to No or N/A where appropriate."
        )

        # ==================================================
        # FORM
        # ==================================================

        with st.form(
            key=f"qa_form_{selected_qa_id}"
        ):

            answers = {}

            # --------------------------------------------------
            # 28 Parameters
            # --------------------------------------------------

            for parameter_id, question in enumerate(
                QA_QUESTIONS,
                start=1
            ):

                fatal_label = ""

                if parameter_id in FATAL_PARAMETERS:

                    fatal_label = (
                        " ⚠️ FATAL"
                    )

                st.markdown(
                    f"**{parameter_id}. "
                    f"{question}"
                    f"{fatal_label}**"
                )

                previous_answer = current_answers.get(
                    parameter_id,
                    "Yes"
                )

                options = [
                    "Yes",
                    "No",
                    "N/A"
                ]

                if previous_answer not in options:

                    previous_answer = "Yes"

                answer = st.radio(
                    label=f"Parameter {parameter_id}",
                    options=options,
                    index=options.index(
                        previous_answer
                    ),
                    horizontal=True,
                    key=(
                        f"answer_"
                        f"{selected_qa_id}_"
                        f"{parameter_id}"
                    ),
                    label_visibility="collapsed"
                )

                answers[
                    parameter_id
                ] = answer

                st.divider()

            # ==================================================
            # FINAL DECISION
            # ==================================================

            st.subheader(
                "Final QA Decision"
            )

            previous_final_result = current_answers.get(
                "final_result",
                ""
            )

            final_result_options = [
                "Select Final Result"
            ] + FINAL_RESULTS

            if previous_final_result in FINAL_RESULTS:

                final_index = final_result_options.index(
                    previous_final_result
                )

            else:

                final_index = 0

            final_result = st.selectbox(
                "Final result for this sale",
                final_result_options,
                index=final_index
            )

            # ==================================================
            # COMMENTS
            # ==================================================

            comments = st.text_area(
                "QA Comments",
                value=current_answers.get(
                    "comments",
                    ""
                ),
                placeholder=(
                    "Enter observations, reasons for rejection, "
                    "rework requirements, hold reasons, etc."
                )
            )

            st.write("")

            # ==================================================
            # BUTTONS
            # ==================================================

            save_progress = st.form_submit_button(
                "💾 SAVE PROGRESS",
                use_container_width=True
            )

            submit_final = st.form_submit_button(
                "✅ SUBMIT FINAL QA",
                type="primary",
                use_container_width=True
            )

        # ==================================================
        # SAVE PROGRESS
        # ==================================================

        if save_progress:

            answers["final_result"] = (
                final_result
                if final_result != "Select Final Result"
                else ""
            )

            answers["comments"] = comments

            # Store answers
            st.session_state[
                "qa_answers"
            ][selected_qa_id] = answers

            # Current score
            score = calculate_score(
                answers
            )

            fatal_failure = has_fatal_failure(
                answers
            )

            # Update sale
            df.loc[
                df["QA_ID"]
                == selected_qa_id,
                "QA_Score"
            ] = score

            df.loc[
                df["QA_ID"]
                == selected_qa_id,
                "Fatal_Failure"
            ] = fatal_failure

            df.loc[
                df["QA_ID"]
                == selected_qa_id,
                "QA_Comments"
            ] = comments

            # Keep pending
            df.loc[
                df["QA_ID"]
                == selected_qa_id,
                "QA_Status"
            ] = "Quality Pending"

            st.session_state[
                "sales_data"
            ] = df

            st.success(
                f"Progress saved for "
                f"{safe_value(sale, 'Customer_Name')}."
            )

        # ==================================================
        # FINAL SUBMISSION
        # ==================================================

        if submit_final:

            if final_result == "Select Final Result":

                st.error(
                    "Please select a Final QA Result "
                    "before submitting."
                )

            else:

                # Save answers
                answers[
                    "final_result"
                ] = final_result

                answers[
                    "comments"
                ] = comments

                st.session_state[
                    "qa_answers"
                ][selected_qa_id] = answers

                # Calculate
                score = calculate_score(
                    answers
                )

                fatal_failure = has_fatal_failure(
                    answers
                )

                # Update sale
                df.loc[
                    df["QA_ID"]
                    == selected_qa_id,
                    "QA_Status"
                ] = "Completed"

                df.loc[
                    df["QA_ID"]
                    == selected_qa_id,
                    "QA_Score"
                ] = score

                df.loc[
                    df["QA_ID"]
                    == selected_qa_id,
                    "Fatal_Failure"
                ] = fatal_failure

                df.loc[
                    df["QA_ID"]
                    == selected_qa_id,
                    "Final_QA_Result"
                ] = final_result

                df.loc[
                    df["QA_ID"]
                    == selected_qa_id,
                    "QA_Comments"
                ] = comments

                st.session_state[
                    "sales_data"
                ] = df

                # ------------------------------------------
                # Display result
                # ------------------------------------------

                st.divider()

                if final_result == "Approved":

                    st.success(
                        "SALE QA COMPLETED — APPROVED"
                    )

                elif final_result == "Rejected":

                    st.error(
                        "SALE QA COMPLETED — REJECTED"
                    )

                elif final_result == "Cancelled":

                    st.warning(
                        "SALE QA COMPLETED — CANCELLED"
                    )

                elif final_result == "Reworked Required":

                    st.warning(
                        "SALE QA COMPLETED — REWORK REQUIRED"
                    )

                elif final_result == "Hold":

                    st.info(
                        "SALE QA COMPLETED — ON HOLD"
                    )

                col1, col2, col3 = st.columns(3)

                with col1:

                    st.metric(
                        "Quality Score",
                        f"{score:.2f}%"
                    )

                with col2:

                    st.metric(
                        "Fatal Failure",
                        "YES"
                        if fatal_failure
                        else "NO"
                    )

                with col3:

                    st.metric(
                        "Final QA Result",
                        final_result
                    )

    # ======================================================
    # CURRENT RESULTS
    # ======================================================

    st.divider()

    st.subheader(
        "Current QA Results"
    )

    result_columns = [
        "QA_ID",
        "Sale_Date",
        "Agent",
        "Verifier",
        "Customer_Name",
        "QA_Status",
        "QA_Score",
        "Fatal_Failure",
        "Final_QA_Result",
        "QA_Comments"
    ]

    results_df = df[
        result_columns
    ].copy()

    st.dataframe(
        results_df,
        use_container_width=True,
        hide_index=True
    )

    # ======================================================
    # EXCEL EXPORT
    # ======================================================

    st.divider()

    st.subheader(
        "Export"
    )

    excel_file = create_excel_download(
        df,
        st.session_state[
            "qa_answers"
        ]
    )

    st.download_button(
        label="⬇️ Download QA Excel",
        data=excel_file,
        file_name="Sparta_QA_Results.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        use_container_width=True
    )
