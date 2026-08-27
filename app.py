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
# FIXED FILE STRUCTURE
# ==========================================================

COLUMN_NAMES = [
    "Serial_No",                 # 1
    "Month",                     # 2
    "Agent",                     # 3
    "Verifier",                 # 4
    "Company",                  # 5
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
    "Broadband_Type",            # 29
    "Router_Charges",            # 30
    "Raw_31",                    # 31
    "Raw_32",                    # 32
    "Payment_Frequency",         # 33
    "Payment_Method",            # 34
    "Contract_Duration",         # 35
    "Calling_Package",            # 36
    "Raw_37",                    # 37
    "Enrollment_Fee",            # 38
    "Additional_Notes",          # 39
    "Lead_Source"                # 40
]


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
    {
        "id": 1,
        "question": "Did the agent greet the customer and introduce themselves and the company properly?"
    },
    {
        "id": 2,
        "question": "Did the agent clearly inform the purpose of the call in a professional and customer-centric manner?"
    },
    {
        "id": 3,
        "question": 'Did the agent avoid inappropriate opening remarks (e.g., referring to the customer as "retired or pensioner")?'
    },
    {
        "id": 4,
        "question": "Did the agent confirm the customer’s current service provider and type of line (e.g., copper/fiber)?"
    },
    {
        "id": 5,
        "question": "Did the agent ask about the customer’s current usage or bill amount to tailor their offer?"
    },
    {
        "id": 6,
        "question": "Did the agent confirm if the customer is under contract with their current provider?"
    },
    {
        "id": 7,
        "question": "Did the agent ask about any additional services, for example extension lines, cordless phones, TV, BB and type of BB services (if applicable)?"
    },
    {
        "id": 8,
        "question": "Did the agent appropriately compare Sparta Telecom's offerings with the customer’s current provider's pricing/services?"
    },
    {
        "id": 9,
        "question": "Did the agent verify the customer’s awareness of their current service details (e.g., bills, provider name)?"
    },
    {
        "id": 10,
        "question": "Did the agent confirm today's date or check for signs of vulnerability (e.g., customer being unclear or confused)?"
    },
    {
        "id": 11,
        "question": "Did the agent effectively engage the customer by asking personalized questions (rapport building)?"
    },
    {
        "id": 12,
        "question": "Did the agent explain savings AND quick support services etc. in a way that aligned with the customer's situation?"
    },
    {
        "id": 13,
        "question": "Did the agent offer an appropriate package based on the customer’s usage and preferences?"
    },
    {
        "id": 14,
        "question": "Did the agent explain VAT, call setup fees, and any other charges clearly?"
    },
    {
        "id": 15,
        "question": "Did the agent mention the 24-month price guarantee or any other relevant contract terms?"
    },
    {
        "id": 16,
        "question": "Did the agent clarify that Sparta Telecom is a separate company to avoid confusion?"
    },
    {
        "id": 17,
        "question": "Did the agent collect all necessary details (e.g., Name, DOB, address, email, alternate contact) accurately?"
    },
    {
        "id": 18,
        "question": "Did the agent confirm the customer’s payment mode and attempt to collect direct debit details professionally?"
    },
    {
        "id": 19,
        "question": "Did the agent verify the decision-maker or presence of family interference (if applicable)?"
    },
    {
        "id": 20,
        "question": "Did the agent refrain from mentioning the cooling-off period and customer rights without being asked?"
    },
    {
        "id": 21,
        "question": "Did the agent disclose router charges, line import charges, or broadband downgrade/removal charges if applicable?"
    },
    {
        "id": 22,
        "question": "Did the agent explain any health alarm systems, itemized billing, or calling features if relevant to the package?"
    },
    {
        "id": 23,
        "question": "Did the agent avoid pressuring, compelling, or misleading the customer into agreeing to the sale?"
    },
    {
        "id": 24,
        "question": "Did the agent confirm that the customer is happy and satisfied with the package being offered?"
    },
    {
        "id": 25,
        "question": "Did the agent ensure there was no confusion about proceeding with the package/sale?"
    },
    {
        "id": 26,
        "question": "Did the verifier perform the script verbatim and follow compliance guidelines?"
    },
    {
        "id": 27,
        "question": "Did the verifier ensure all customer details and payment details were accurate and matched the recorded sale?"
    },
    {
        "id": 28,
        "question": "Did the verifier confirm that the sale was properly explained and not based solely on paperwork?"
    }
]


# ==========================================================
# FATAL PARAMETERS
# ==========================================================

# We will define these later.
FATAL_PARAMETERS = set()


# ==========================================================
# SCORING FUNCTIONS
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
    """
    Returns True when a fatal parameter is answered No.
    """

    for parameter_id in FATAL_PARAMETERS:

        if answers.get(parameter_id) == "No":
            return True

    return False


def calculate_qa_status(answers):
    """
    Numerical QA status based on score/fatal failure.

    This is separate from the final QA decision.
    """

    score = calculate_score(answers)

    if has_fatal_failure(answers):
        return "FAIL"

    if score >= 80:
        return "PASS"

    return "FAIL"


# ==========================================================
# EXCEL EXPORT FUNCTION
# ==========================================================

def create_excel_download(df):

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="xlsxwriter"
    ) as writer:

        # ----------------------------------------------
        # All sales
        # ----------------------------------------------

        df.to_excel(
            writer,
            sheet_name="QA Results",
            index=False
        )

        # ----------------------------------------------
        # Summary
        # ----------------------------------------------

        summary_data = {
            "Metric": [
                "Total Sales",
                "Quality Pending",
                "Completed",
                "Approved",
                "Rejected",
                "Cancelled",
                "Reworked Required",
                "Hold",
                "Fatal Failures"
            ],
            "Count": [
                len(df),
                (df["QA_Status"] == "Quality Pending").sum(),
                (df["QA_Status"] == "Completed").sum(),
                (df["Final_QA_Result"] == "Approved").sum(),
                (df["Final_QA_Result"] == "Rejected").sum(),
                (df["Final_QA_Result"] == "Cancelled").sum(),
                (df["Final_QA_Result"] == "Reworked Required").sum(),
                (df["Final_QA_Result"] == "Hold").sum(),
                df["Fatal_Failure"].fillna(False).sum()
            ]
        }

        summary_df = pd.DataFrame(summary_data)

        summary_df.to_excel(
            writer,
            sheet_name="Summary",
            index=False
        )

        # ----------------------------------------------
        # Agent summary
        # ----------------------------------------------

        agent_summary = (
            df.groupby("Agent", dropna=False)
            .agg(
                Sales=("QA_ID", "count"),
                Completed=("QA_Status", lambda x: (x == "Completed").sum()),
                Average_Score=("QA_Score", "mean"),
                Approved=("Final_QA_Result", lambda x: (x == "Approved").sum()),
                Rejected=("Final_QA_Result", lambda x: (x == "Rejected").sum()),
                Cancelled=("Final_QA_Result", lambda x: (x == "Cancelled").sum()),
                Reworked=("Final_QA_Result", lambda x: (x == "Reworked Required").sum()),
                Hold=("Final_QA_Result", lambda x: (x == "Hold").sum()),
                Fatal_Failures=("Fatal_Failure", "sum")
            )
            .reset_index()
        )

        agent_summary["Average_Score"] = (
            agent_summary["Average_Score"]
            .round(2)
        )

        agent_summary.to_excel(
            writer,
            sheet_name="Agent Summary",
            index=False
        )

    output.seek(0)

    return output


# ==========================================================
# HEADER
# ==========================================================

st.title("Sparta QA Checker")

st.caption(
    "Upload sales → complete QA → assign final result → export."
)


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

        df = pd.read_excel(
            uploaded_file,
            header=None
        )

        expected_columns = len(COLUMN_NAMES)
        actual_columns = df.shape[1]

        if actual_columns != expected_columns:

            st.error(
                f"Unexpected file structure. "
                f"Expected {expected_columns} columns, "
                f"but found {actual_columns} columns."
            )

            st.stop()

        # Apply internal names
        df.columns = COLUMN_NAMES

        # Remove fully blank rows
        df = df.dropna(
            how="all"
        ).reset_index(drop=True)

        # --------------------------------------------------
        # Create QA fields
        # --------------------------------------------------

        df["QA_ID"] = range(
            1,
            len(df) + 1
        )

        df["QA_Status"] = "Quality Pending"
        df["QA_Score"] = None
        df["Fatal_Failure"] = False
        df["QA_Status_Result"] = None
        df["Final_QA_Result"] = ""
        df["QA_Comments"] = ""

        # --------------------------------------------------
        # Store data
        # --------------------------------------------------

        st.session_state["sales_data"] = df

        if "qa_answers" not in st.session_state:
            st.session_state["qa_answers"] = {}

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

    df = st.session_state["sales_data"]

    # ======================================================
    # DASHBOARD
    # ======================================================

    st.divider()

    st.subheader("QA Dashboard")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "Total Sales",
            len(df)
        )

    with col2:
        st.metric(
            "Pending",
            (df["QA_Status"] == "Quality Pending").sum()
        )

    with col3:
        st.metric(
            "Completed",
            (df["QA_Status"] == "Completed").sum()
        )

    with col4:
        st.metric(
            "Approved",
            (df["Final_QA_Result"] == "Approved").sum()
        )

    with col5:
        st.metric(
            "Rejected",
            (df["Final_QA_Result"] == "Rejected").sum()
        )

    # ======================================================
    # FILTERS
    # ======================================================

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:

        agents = ["All"] + sorted(
            df["Agent"]
            .fillna("")
            .astype(str)
            .unique()
            .tolist()
        )

        selected_agent = st.selectbox(
            "Filter by Agent",
            agents
        )

    # Build filtered data first
    filtered_df = df.copy()

    if selected_agent != "All":

        filtered_df = filtered_df[
            filtered_df["Agent"].astype(str)
            == selected_agent
        ]

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

    with col3:

        result_filter = st.selectbox(
            "Final Result",
            ["All"] + FINAL_RESULTS
        )

    if result_filter != "All":

        filtered_df = filtered_df[
            filtered_df["Final_QA_Result"]
            == result_filter
        ]

    # ======================================================
    # SALE SELECTOR
    # ======================================================

    st.divider()

    st.subheader("Select Sale for Quality Check")

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
            format_func=lambda x: (
                f"QA #{x} — "
                f"{df.loc[df['QA_ID'] == x, 'Customer_Name'].iloc[0]} "
                f"— "
                f"{df.loc[df['QA_ID'] == x, 'Agent'].iloc[0]}"
            )
        )

        # ==================================================
        # SELECTED SALE
        # ==================================================

        sale = df[
            df["QA_ID"] == selected_qa_id
        ].iloc[0]

        st.divider()

        st.subheader("Sale Details")

        detail1, detail2, detail3, detail4 = st.columns(4)

        with detail1:
            st.write("**Customer**")
            st.write(sale["Customer_Name"])

        with detail2:
            st.write("**Agent**")
            st.write(sale["Agent"])

        with detail3:
            st.write("**Verifier**")
            st.write(sale["Verifier"])

        with detail4:
            st.write("**Sale Date**")
            st.write(sale["Sale_Date"])

        detail1, detail2, detail3, detail4 = st.columns(4)

        with detail1:
            st.write("**Phone**")
            st.write(sale["Phone"])

        with detail2:
            st.write("**Current Provider**")
            st.write(sale["Current_Provider"])

        with detail3:
            st.write("**Package Offered**")
            st.write(sale["Package_Offered"])

        with detail4:
            st.write("**Broadband**")
            st.write(sale["Broadband_Type"])

        # ==================================================
        # QA CHECKLIST
        # ==================================================

        st.divider()

        st.subheader("Quality Checklist")

        st.info(
            "Answer all applicable questions. "
            "Use N/A where the question genuinely does not apply."
        )

        current_answers = st.session_state[
            "qa_answers"
        ].get(
            selected_qa_id,
            {}
        )

        with st.form(
            key=f"qa_form_{selected_qa_id}"
        ):

            answers = {}

            for item in QA_QUESTIONS:

                parameter_id = item["id"]

                fatal_label = ""

                if parameter_id in FATAL_PARAMETERS:
                    fatal_label = " ⚠️ FATAL"

                st.markdown(
                    f"**{parameter_id}. "
                    f"{item['question']}{fatal_label}**"
                )

                previous_answer = current_answers.get(
                    parameter_id,
                    "Yes"
                )

                answer = st.radio(
                    label=f"Parameter {parameter_id}",
                    options=["Yes", "No", "N/A"],
                    index=[
                        "Yes",
                        "No",
                        "N/A"
                    ].index(previous_answer),
                    horizontal=True,
                    key=f"answer_{selected_qa_id}_{parameter_id}",
                    label_visibility="collapsed"
                )

                answers[parameter_id] = answer

                st.divider()

            # --------------------------------------------------
            # FINAL RESULT
            # --------------------------------------------------

            st.subheader("Final QA Decision")

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

            # --------------------------------------------------
            # COMMENTS
            # --------------------------------------------------

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

            submitted = st.form_submit_button(
                "SUBMIT QA RESULT",
                type="primary",
                use_container_width=True
            )

        # ==================================================
        # SUBMIT
        # ==================================================

        if submitted:

            if final_result == "Select Final Result":

                st.error(
                    "Please select a Final QA Result before submitting."
                )

            else:

                score = calculate_score(
                    answers
                )

                fatal_failure = has_fatal_failure(
                    answers
                )

                qa_status_result = calculate_qa_status(
                    answers
                )

                answers["final_result"] = final_result
                answers["comments"] = comments

                st.session_state[
                    "qa_answers"
                ][selected_qa_id] = answers

                # ------------------------------------------
                # Update sale
                # ------------------------------------------

                df.loc[
                    df["QA_ID"] == selected_qa_id,
                    "QA_Status"
                ] = "Completed"

                df.loc[
                    df["QA_ID"] == selected_qa_id,
                    "QA_Score"
                ] = score

                df.loc[
                    df["QA_ID"] == selected_qa_id,
                    "Fatal_Failure"
                ] = fatal_failure

                df.loc[
                    df["QA_ID"] == selected_qa_id,
                    "QA_Status_Result"
                ] = qa_status_result

                df.loc[
                    df["QA_ID"] == selected_qa_id,
                    "Final_QA_Result"
                ] = final_result

                df.loc[
                    df["QA_ID"] == selected_qa_id,
                    "QA_Comments"
                ] = comments

                st.session_state[
                    "sales_data"
                ] = df

                # ------------------------------------------
                # Result display
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
                        "YES" if fatal_failure else "NO"
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

    st.subheader("Current QA Results")

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

    results_df = df[result_columns].copy()

    st.dataframe(
        results_df,
        use_container_width=True,
        hide_index=True
    )

    # ======================================================
    # DOWNLOAD EXCEL
    # ======================================================

    st.divider()

    st.subheader("Export")

    excel_file = create_excel_download(
        df
    )

    st.download_button(
        label="Download QA Results Excel",
        data=excel_file,
        file_name="Sparta_QA_Results.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        use_container_width=True
    )
