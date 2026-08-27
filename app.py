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
    "Broadband_Type",            # 29
    "Router_Charges",            # 30
    "Raw_31",                    # 31
    "Raw_32",                    # 32
    "Payment_Frequency",         # 33
    "Payment_Method",            # 34
    "Contract_Duration",         # 35
    "Calling_Package",           # 36
    "Raw_37",                    # 37
    "Enrollment_Fee",            # 38
    "Additional_Notes",          # 39
    "Lead_Source"                # 40
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

# Put the parameter numbers that should automatically fail a sale
# in this set.
#
# Example:
# FATAL_PARAMETERS = {23, 27}
#
# For now this is empty until we define the fatal parameters.

FATAL_PARAMETERS = set()


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

def calculate_score(answers):
    """
    Calculate percentage based only on Yes/No answers.
    N/A answers are excluded.
    """

    applicable = [
        answer
        for answer in answers.values()
        if answer in ["Yes", "No"]
    ]

    if not applicable:
        return 0.0

    yes_count = sum(
        1 for answer in applicable
        if answer == "Yes"
    )

    return round(
        (yes_count / len(applicable)) * 100,
        2
    )


def has_fatal_failure(answers):
    """
    Return True if any fatal parameter has been answered No.
    """

    for parameter_id in FATAL_PARAMETERS:

        if answers.get(parameter_id) == "No":
            return True

    return False


def calculate_result(answers):
    """
    Determine final result.
    """

    if has_fatal_failure(answers):
        return "FAIL"

    score = calculate_score(answers)

    # Temporary pass threshold.
    # We can change this later.
    if score >= 80:
        return "PASS"

    return "FAIL"


# ==========================================================
# HEADER
# ==========================================================

st.title("Sparta QA Checker")

st.caption(
    "Upload sales → select a sale → complete the 28-point QA checklist."
)


# ==========================================================
# FILE UPLOAD
# ==========================================================

uploaded_file = st.file_uploader(
    "Upload Daily Sales Excel File",
    type=["xlsx", "xls"]
)


# ==========================================================
# READ UPLOAD
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

        # Apply fixed column names
        df.columns = COLUMN_NAMES

        # --------------------------------------------------
        # Remove completely empty rows
        # --------------------------------------------------

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
        df["QA_Result"] = None
        df["QA_Comments"] = ""

        # --------------------------------------------------
        # Keep uploaded data in session
        # --------------------------------------------------

        st.session_state["sales_data"] = df

        # Create answer storage
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
# MAIN APPLICATION
# ==========================================================

if "sales_data" in st.session_state:

    df = st.session_state["sales_data"]

    # ======================================================
    # SUMMARY
    # ======================================================

    st.divider()

    st.subheader("QA Dashboard")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Sales",
            len(df)
        )

    with col2:
        st.metric(
            "Quality Pending",
            int(
                (df["QA_Status"] == "Quality Pending").sum()
            )
        )

    with col3:
        st.metric(
            "Completed",
            int(
                (df["QA_Status"] == "Completed").sum()
            )
        )

    with col4:
        st.metric(
            "Failed",
            int(
                (df["QA_Result"] == "FAIL").sum()
            )
        )

    # ======================================================
    # SALE SELECTION
    # ======================================================

    st.divider()

    st.subheader("Select Sale")

    col1, col2 = st.columns(2)

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

    with col2:

        available_df = df.copy()

        if selected_agent != "All":
            available_df = available_df[
                available_df["Agent"].astype(str)
                == selected_agent
            ]

        sale_options = available_df[
            "QA_ID"
        ].tolist()

        selected_qa_id = st.selectbox(
            "Select Sale",
            sale_options,
            format_func=lambda x: (
                f"QA #{x} — "
                f"{df.loc[df['QA_ID'] == x, 'Customer_Name'].iloc[0]} "
                f"— Agent: "
                f"{df.loc[df['QA_ID'] == x, 'Agent'].iloc[0]}"
            )
        )

    # ======================================================
    # SELECTED SALE
    # ======================================================

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

    # ======================================================
    # QA CHECKLIST
    # ======================================================

    st.divider()

    st.subheader("Quality Checklist")

    st.info(
        "Answer every applicable question. "
        "Use N/A where the parameter genuinely does not apply."
    )

    # Retrieve previous answers for this sale
    current_answers = st.session_state[
        "qa_answers"
    ].get(
        selected_qa_id,
        {}
    )

    # Create form
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
                index=["Yes", "No", "N/A"].index(
                    previous_answer
                ),
                horizontal=True,
                key=f"answer_{selected_qa_id}_{parameter_id}",
                label_visibility="collapsed"
            )

            answers[parameter_id] = answer

            st.divider()

        comments = st.text_area(
            "QA Comments",
            value=current_answers.get(
                "comments",
                ""
            ),
            placeholder="Enter any observations or comments..."
        )

        submitted = st.form_submit_button(
            "SUBMIT QA",
            type="primary",
            use_container_width=True
        )

    # ======================================================
    # SUBMIT QA
    # ======================================================

    if submitted:

        score = calculate_score(
            answers
        )

        fatal_failure = has_fatal_failure(
            answers
        )

        result = calculate_result(
            answers
        )

        # Save answers
        answers["comments"] = comments

        st.session_state[
            "qa_answers"
        ][selected_qa_id] = answers

        # Update master dataframe
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
            "QA_Result"
        ] = result

        df.loc[
            df["QA_ID"] == selected_qa_id,
            "QA_Comments"
        ] = comments

        st.session_state[
            "sales_data"
        ] = df

        # --------------------------------------------------
        # Result display
        # --------------------------------------------------

        st.divider()

        if result == "PASS":

            st.success(
                f"QA COMPLETED — PASS"
            )

        else:

            st.error(
                f"QA COMPLETED — FAIL"
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
                "Final Result",
                result
            )


# ==========================================================
# CURRENT QA RESULTS
# ==========================================================

if "sales_data" in st.session_state:

    st.divider()

    st.subheader("QA Results")

    result_columns = [
        "QA_ID",
        "Sale_Date",
        "Agent",
        "Customer_Name",
        "QA_Status",
        "QA_Score",
        "Fatal_Failure",
        "QA_Result"
    ]

    results_df = st.session_state[
        "sales_data"
    ][result_columns].copy()

    st.dataframe(
        results_df,
        use_container_width=True,
        hide_index=True
    )
