import streamlit as st
import pandas as pd
import gspread
import hashlib

from io import BytesIO
from datetime import datetime

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
# GOOGLE SHEET CONFIG
# ==========================================================

GOOGLE_SHEET_ID = (
    "1Rk1sxO6rcJze5TTMI-7wz8x63Mw_r8qLB63Q2TPe9H4"
)

QA_RECORDS_SHEET = "QA Records"
QA_ANSWERS_SHEET = "QA Answers"
QA_PARAMETERS_SHEET = "QA Parameters"
AGENT_SUMMARY_SHEET = "Agent Summary"


# ==========================================================
# FIXED 40-COLUMN INPUT FILE
# ==========================================================

COLUMN_NAMES = [
    "Serial_No",
    "Month",
    "Agent",
    "Verifier",
    "Company",
    "Sale_Date",
    "Raw_7",
    "Raw_8",
    "Customer_Name",
    "Phone",
    "Raw_11",
    "Raw_12",
    "Raw_13",
    "Raw_14",
    "Raw_15",
    "Raw_16",
    "Raw_17",
    "Confirmation",
    "Date_of_Birth",
    "Current_Provider",
    "Customer_Address",
    "Bank_Name",
    "Raw_23",
    "Raw_24",
    "Raw_25",
    "Raw_26",
    "Package_Offered",
    "Service",
    "Raw_28",
    "Broadband_Type",
    "Router_Charges",
    "Raw_31",
    "Raw_32",
    "Payment_Frequency",
    "Payment_Method",
    "Contract_Duration",
    "Calling_Feature",
    "Raw_37",
    "Bill_Cost",
    "Additional_Notes",
    "Lead_Source"
]

# Correct the accidental 41-column issue above by enforcing
# the exact mapping provided for the input file.
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
#
# Add parameter numbers here once your fatal list is finalised.
#
# Example:
# FATAL_PARAMETERS = {3, 23, 27}
#
# ==========================================================

FATAL_PARAMETERS = set()


# ==========================================================
# SESSION STATE
# ==========================================================

if "sales_data" not in st.session_state:
    st.session_state["sales_data"] = None

if "qa_answers" not in st.session_state:
    st.session_state["qa_answers"] = {}

if "uploaded_file_key" not in st.session_state:
    st.session_state["uploaded_file_key"] = None

if "dashboard_df" not in st.session_state:
    st.session_state["dashboard_df"] = None

if "dashboard_answers" not in st.session_state:
    st.session_state["dashboard_answers"] = {}

if "dashboard_loaded" not in st.session_state:
    st.session_state["dashboard_loaded"] = False


# ==========================================================
# BASIC HELPERS
# ==========================================================

def safe_value(row, column_name):
    """
    Safely retrieve a value from a pandas Series/row.
    """

    if column_name not in row.index:
        return ""

    value = row[column_name]

    if pd.isna(value):
        return ""

    return str(value).strip()


def current_timestamp():
    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def make_editable_dataframe(df):
    """
    Convert writable columns to object dtype.

    IMPORTANT:
    The dashboard update bug on Pandas 3/Arrow was caused
    by some columns remaining as Arrow-backed strings.

    We therefore convert ALL columns to object here.
    This makes the dataframe safe for mixed-type assignments.
    """

    if df is None:
        return None

    df = df.copy()

    try:
        df = df.astype(object)
    except Exception:
        pass

    return df


# ==========================================================
# QA ID
# ==========================================================

def generate_qa_id(row):
    """
    Generate a stable QA ID from the identifying sale fields.
    """

    source = "|".join([
        safe_value(row, "Serial_No"),
        safe_value(row, "Sale_Date"),
        safe_value(row, "Agent"),
        safe_value(row, "Phone"),
        safe_value(row, "Customer_Name")
    ])

    digest = hashlib.sha1(
        source.encode("utf-8")
    ).hexdigest()[:12]

    return f"QA-{digest.upper()}"


# ==========================================================
# PREPARE DATAFRAME
# ==========================================================

def prepare_dataframe(df):

    if df is None:
        return None

    df = df.copy()

    # ------------------------------------------------------
    # Make sure original fields exist
    # ------------------------------------------------------

    for column in COLUMN_NAMES:

        if column not in df.columns:

            df[column] = ""

    # ------------------------------------------------------
    # QA ID
    # ------------------------------------------------------

    if "QA_ID" not in df.columns:

        df["QA_ID"] = df.apply(
            generate_qa_id,
            axis=1
        )

    # ------------------------------------------------------
    # Defaults
    # ------------------------------------------------------

    defaults = {
        "QA_Status": "Quality Pending",
        "QA_Score": None,
        "Fatal_Failure": False,
        "Final_QA_Result": "",
        "QA_Comments": "",
        "Evaluator_Name": "",
        "Campaign_Line": "",
        "Call_Disposition": "",
        "Next_Review_Date": "",
        "Call_Summary": "",
        "Goods": "",
        "Bads": "",
        "Dos": "",
        "Donts": "",
        "Actionable_Coaching": "",
        "Created_At": current_timestamp(),
        "Last_Updated": current_timestamp()
    }

    for column, default_value in defaults.items():

        if column not in df.columns:

            df[column] = default_value

    return make_editable_dataframe(
        df
    )


# ==========================================================
# SCORING
# ==========================================================

def calculate_score(answers):

    applicable_answers = []

    for key, answer in answers.items():

        if isinstance(key, int):

            if answer in [
                "Yes",
                "No"
            ]:

                applicable_answers.append(
                    answer
                )

    if not applicable_answers:

        return 0.0

    yes_count = sum(
        answer == "Yes"
        for answer in applicable_answers
    )

    return round(
        (
            yes_count
            / len(applicable_answers)
        ) * 100,
        2
    )


def has_fatal_failure(answers):

    for parameter_id in FATAL_PARAMETERS:

        if answers.get(
            parameter_id
        ) == "No":

            return True

    return False


# ==========================================================
# GOOGLE CONNECTION
# ==========================================================

@st.cache_resource
def get_google_client():

    if "gcp_service_account" not in st.secrets:

        raise RuntimeError(
            "gcp_service_account is missing "
            "from Streamlit Secrets."
        )

    credentials = (
        Credentials.from_service_account_info(
            dict(
                st.secrets[
                    "gcp_service_account"
                ]
            ),
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
    )

    return gspread.authorize(
        credentials
    )


def get_spreadsheet():

    return get_google_client().open_by_key(
        GOOGLE_SHEET_ID
    )


# ==========================================================
# GOOGLE SHEET INITIALISATION
# ==========================================================

def ensure_worksheet(
    spreadsheet,
    title,
    headers
):

    try:

        worksheet = spreadsheet.worksheet(
            title
        )

    except gspread.WorksheetNotFound:

        worksheet = spreadsheet.add_worksheet(
            title=title,
            rows=1000,
            cols=max(
                50,
                len(headers) + 5
            )
        )

        worksheet.update(
            "A1",
            [headers]
        )

        return worksheet

    current_values = worksheet.get_all_values()

    if not current_values:

        worksheet.update(
            "A1",
            [headers]
        )

    return worksheet


def initialise_google_sheets():

    spreadsheet = get_spreadsheet()

    # ------------------------------------------------------
    # QA RECORDS
    # ------------------------------------------------------

    records_headers = (
        COLUMN_NAMES
        + [
            "QA_ID",
            "QA_Status",
            "QA_Score",
            "Fatal_Failure",
            "Final_QA_Result",
            "QA_Comments",
            "Evaluator_Name",
            "Campaign_Line",
            "Call_Disposition",
            "Next_Review_Date",
            "Call_Summary",
            "Goods",
            "Bads",
            "Dos",
            "Donts",
            "Actionable_Coaching",
            "Created_At",
            "Last_Updated"
        ]
    )

    records_ws = ensure_worksheet(
        spreadsheet,
        QA_RECORDS_SHEET,
        records_headers
    )

    # ------------------------------------------------------
    # QA ANSWERS
    # ------------------------------------------------------

    answer_headers = (
        ["QA_ID"]
        + [
            f"Parameter_{i}"
            for i in range(1, 29)
        ]
        + [
            "Last_Updated"
        ]
    )

    answers_ws = ensure_worksheet(
        spreadsheet,
        QA_ANSWERS_SHEET,
        answer_headers
    )

    # ------------------------------------------------------
    # QA PARAMETERS
    # ------------------------------------------------------

    parameter_headers = [
        "Parameter_ID",
        "Question",
        "Fatal",
        "Weight",
        "Active"
    ]

    parameters_ws = ensure_worksheet(
        spreadsheet,
        QA_PARAMETERS_SHEET,
        parameter_headers
    )

    existing_parameters = (
        parameters_ws.get_all_values()
    )

    if len(existing_parameters) <= 1:

        parameter_rows = []

        for parameter_id, question in enumerate(
            QA_QUESTIONS,
            start=1
        ):

            parameter_rows.append([
                parameter_id,
                question,
                (
                    "Yes"
                    if parameter_id in FATAL_PARAMETERS
                    else "No"
                ),
                1,
                "Yes"
            ])

        if parameter_rows:

            parameters_ws.append_rows(
                parameter_rows,
                value_input_option="USER_ENTERED"
            )

    # ------------------------------------------------------
    # AGENT SUMMARY
    # ------------------------------------------------------

    summary_headers = [
        "Agent",
        "Sales Checked",
        "Average QA Score",
        "Approved",
        "Rejected",
        "Cancelled",
        "Reworked Required",
        "Hold",
        "Fatal Failures"
    ]

    summary_ws = ensure_worksheet(
        spreadsheet,
        AGENT_SUMMARY_SHEET,
        summary_headers
    )

    return {
        "records": records_ws,
        "answers": answers_ws,
        "parameters": parameters_ws,
        "summary": summary_ws
    }


# ==========================================================
# COLUMN LETTER
# ==========================================================

def column_letter(number):

    result = ""

    while number > 0:

        number, remainder = divmod(
            number - 1,
            26
        )

        result = (
            chr(
                65 + remainder
            )
            + result
        )

    return result


# ==========================================================
# FIND GOOGLE ROW BY QA ID
# ==========================================================

def find_google_row(
    worksheet,
    qa_id
):

    records = worksheet.get_all_records()

    for row_number, record in enumerate(
        records,
        start=2
    ):

        if str(
            record.get(
                "QA_ID",
                ""
            )
        ).strip() == str(
            qa_id
        ).strip():

            return row_number

    return None


# ==========================================================
# SALE ROW → GOOGLE VALUES
# ==========================================================

def row_to_google_values(row):

    values = []

    # ------------------------------------------------------
    # Original columns
    # ------------------------------------------------------

    for column in COLUMN_NAMES:

        values.append(
            safe_value(
                row,
                column
            )
        )

    # ------------------------------------------------------
    # QA fields
    # ------------------------------------------------------

    extra_columns = [
        "QA_ID",
        "QA_Status",
        "QA_Score",
        "Fatal_Failure",
        "Final_QA_Result",
        "QA_Comments",
        "Evaluator_Name",
        "Campaign_Line",
        "Call_Disposition",
        "Next_Review_Date",
        "Call_Summary",
        "Goods",
        "Bads",
        "Dos",
        "Donts",
        "Actionable_Coaching",
        "Created_At",
        "Last_Updated"
    ]

    for column in extra_columns:

        if column not in row.index:

            values.append("")

            continue

        value = row[column]

        if pd.isna(value):

            values.append("")

        elif isinstance(
            value,
            bool
        ):

            values.append(
                "TRUE"
                if value
                else "FALSE"
            )

        else:

            values.append(
                str(value)
            )

    return values


# ==========================================================
# SAVE SALE TO GOOGLE
# ==========================================================

def save_sale_to_google(
    sale_row,
    answers
):

    sheets = initialise_google_sheets()

    records_ws = sheets[
        "records"
    ]

    answers_ws = sheets[
        "answers"
    ]

    qa_id = safe_value(
        sale_row,
        "QA_ID"
    )

    # ------------------------------------------------------
    # Main record
    # ------------------------------------------------------

    record_values = row_to_google_values(
        sale_row
    )

    existing_record_row = find_google_row(
        records_ws,
        qa_id
    )

    last_column = column_letter(
        len(record_values)
    )

    if existing_record_row:

        records_ws.update(
            f"A{existing_record_row}:"
            f"{last_column}{existing_record_row}",
            [record_values],
            value_input_option="USER_ENTERED"
        )

    else:

        records_ws.append_row(
            record_values,
            value_input_option="USER_ENTERED"
        )

    # ------------------------------------------------------
    # Parameter answers
    # ------------------------------------------------------

    answer_values = [
        qa_id
    ]

    for parameter_id in range(
        1,
        29
    ):

        answer_values.append(
            answers.get(
                parameter_id,
                "Yes"
            )
        )

    answer_values.append(
        current_timestamp()
    )

    existing_answer_row = find_google_row(
        answers_ws,
        qa_id
    )

    last_column = column_letter(
        len(answer_values)
    )

    if existing_answer_row:

        answers_ws.update(
            f"A{existing_answer_row}:"
            f"{last_column}{existing_answer_row}",
            [answer_values],
            value_input_option="USER_ENTERED"
        )

    else:

        answers_ws.append_row(
            answer_values,
            value_input_option="USER_ENTERED"
        )


# ==========================================================
# GOOGLE → APP
# ==========================================================

def sync_from_google():

    sheets = initialise_google_sheets()

    records = (
        sheets["records"]
        .get_all_records()
    )

    if not records:

        return None, {}

    records_df = pd.DataFrame(
        records
    )

    records_df = prepare_dataframe(
        records_df
    )

    # ------------------------------------------------------
    # QA Score
    # ------------------------------------------------------

    records_df["QA_Score"] = pd.to_numeric(
        records_df["QA_Score"],
        errors="coerce"
    ).astype(object)

    # ------------------------------------------------------
    # Fatal Failure
    # ------------------------------------------------------

    records_df["Fatal_Failure"] = (
        records_df["Fatal_Failure"]
        .astype(str)
        .str.upper()
        .isin([
            "TRUE",
            "YES",
            "1"
        ])
        .astype(object)
    )

    # ------------------------------------------------------
    # Answer records
    # ------------------------------------------------------

    answer_records = (
        sheets["answers"]
        .get_all_records()
    )

    qa_answers = {}

    for record in answer_records:

        qa_id = str(
            record.get(
                "QA_ID",
                ""
            )
        ).strip()

        if not qa_id:

            continue

        answers = {}

        for parameter_id in range(
            1,
            29
        ):

            answer = record.get(
                f"Parameter_{parameter_id}",
                "Yes"
            )

            if answer not in [
                "Yes",
                "No",
                "N/A"
            ]:

                answer = "Yes"

            answers[
                parameter_id
            ] = answer

        # --------------------------------------------------
        # Main QA/report record
        # --------------------------------------------------

        matching = records_df[
            records_df[
                "QA_ID"
            ].astype(str)
            == qa_id
        ]

        if not matching.empty:

            row = matching.iloc[0]

            answers["final_result"] = safe_value(
                row,
                "Final_QA_Result"
            )

            answers["comments"] = safe_value(
                row,
                "QA_Comments"
            )

            answers["evaluator_name"] = safe_value(
                row,
                "Evaluator_Name"
            )

            answers["campaign_line"] = safe_value(
                row,
                "Campaign_Line"
            )

            answers["call_disposition"] = safe_value(
                row,
                "Call_Disposition"
            )

            answers["next_review_date"] = safe_value(
                row,
                "Next_Review_Date"
            )

            answers["call_summary"] = safe_value(
                row,
                "Call_Summary"
            )

            answers["goods"] = safe_value(
                row,
                "Goods"
            )

            answers["bads"] = safe_value(
                row,
                "Bads"
            )

            answers["dos"] = safe_value(
                row,
                "Dos"
            )

            answers["donts"] = safe_value(
                row,
                "Donts"
            )

            answers["actionable_coaching"] = safe_value(
                row,
                "Actionable_Coaching"
            )

        qa_answers[
            qa_id
        ] = answers

    return (
        make_editable_dataframe(
            records_df
        ),
        qa_answers
    )


# ==========================================================
# UPDATE AGENT SUMMARY
# ==========================================================

def update_agent_summary(df):

    sheets = initialise_google_sheets()

    worksheet = sheets[
        "summary"
    ]

    headers = [
        "Agent",
        "Sales Checked",
        "Average QA Score",
        "Approved",
        "Rejected",
        "Cancelled",
        "Reworked Required",
        "Hold",
        "Fatal Failures"
    ]

    worksheet.clear()

    worksheet.update(
        "A1",
        [headers]
    )

    completed = df[
        df["QA_Status"]
        == "Completed"
    ].copy()

    if completed.empty:

        return

    rows = []

    for agent, group in completed.groupby(
        "Agent",
        dropna=False
    ):

        scores = pd.to_numeric(
            group[
                "QA_Score"
            ],
            errors="coerce"
        )

        average = (
            scores.mean()
            if scores.notna().any()
            else 0
        )

        fatal_series = (
            group[
                "Fatal_Failure"
            ]
            .fillna(False)
            .astype(bool)
        )

        rows.append([
            str(agent),
            len(group),
            round(
                average,
                2
            ),
            int(
                (
                    group[
                        "Final_QA_Result"
                    ]
                    == "Approved"
                ).sum()
            ),
            int(
                (
                    group[
                        "Final_QA_Result"
                    ]
                    == "Rejected"
                ).sum()
            ),
            int(
                (
                    group[
                        "Final_QA_Result"
                    ]
                    == "Cancelled"
                ).sum()
            ),
            int(
                (
                    group[
                        "Final_QA_Result"
                    ]
                    == "Reworked Required"
                ).sum()
            ),
            int(
                (
                    group[
                        "Final_QA_Result"
                    ]
                    == "Hold"
                ).sum()
            ),
            int(
                fatal_series.sum()
            )
        ])

    worksheet.append_rows(
        rows,
        value_input_option="USER_ENTERED"
    )


# ==========================================================
# PARAMETER PERFORMANCE
# ==========================================================

def get_parameter_performance(
    df,
    qa_answers
):

    completed = df[
        df["QA_Status"]
        == "Completed"
    ].copy()

    rows = []

    for parameter_id in range(
        1,
        29
    ):

        yes_count = 0
        no_count = 0
        na_count = 0

        for qa_id in completed[
            "QA_ID"
        ]:

            answers = qa_answers.get(
                qa_id,
                {}
            )

            answer = answers.get(
                parameter_id,
                "Yes"
            )

            if answer == "Yes":

                yes_count += 1

            elif answer == "No":

                no_count += 1

            elif answer == "N/A":

                na_count += 1

        applicable = (
            yes_count
            + no_count
        )

        yes_percentage = (
            round(
                (
                    yes_count
                    / applicable
                ) * 100,
                2
            )
            if applicable
            else 0
        )

        rows.append({
            "Parameter": parameter_id,
            "Question": QA_QUESTIONS[
                parameter_id - 1
            ],
            "Yes": yes_count,
            "No": no_count,
            "N/A": na_count,
            "Applicable": applicable,
            "Yes %": yes_percentage
        })

    return pd.DataFrame(
        rows
    )


# ==========================================================
# EXCEL EXPORT
# ==========================================================

def create_excel_download(
    df,
    qa_answers
):

    output = BytesIO()

    # ------------------------------------------------------
    # QA RESULTS
    # ------------------------------------------------------

    results_columns = [
        "QA_ID",
        "Serial_No",
        "Sale_Date",
        "Agent",
        "Verifier",
        "Company",
        "Customer_Name",
        "Phone",
        "Current_Provider",
        "Customer_Address",
        "Package_Offered",
        "Service",
        "Broadband_Type",
        "Router_Charges",
        "Payment_Frequency",
        "Payment_Method",
        "Contract_Duration",
        "Calling_Feature",
        "Bill_Cost",
        "Lead_Source",
        "QA_Status",
        "QA_Score",
        "Fatal_Failure",
        "Final_QA_Result",
        "Evaluator_Name",
        "Campaign_Line",
        "Call_Disposition",
        "Next_Review_Date",
        "QA_Comments"
    ]

    available_columns = [
        column
        for column in results_columns
        if column in df.columns
    ]

    results_df = df[
        available_columns
    ].copy()

    # ------------------------------------------------------
    # DETAILED QA
    # ------------------------------------------------------

    detailed_rows = []

    for _, row in df.iterrows():

        qa_id = row[
            "QA_ID"
        ]

        answers = qa_answers.get(
            qa_id,
            {}
        )

        detailed_row = {
            "QA_ID": qa_id,
            "Sale_Date": safe_value(
                row,
                "Sale_Date"
            ),
            "Agent": safe_value(
                row,
                "Agent"
            ),
            "Verifier": safe_value(
                row,
                "Verifier"
            ),
            "Customer_Name": safe_value(
                row,
                "Customer_Name"
            ),
            "Phone": safe_value(
                row,
                "Phone"
            ),
            "Current_Provider": safe_value(
                row,
                "Current_Provider"
            ),
            "Package_Offered": safe_value(
                row,
                "Package_Offered"
            ),
            "Service": safe_value(
                row,
                "Service"
            ),
            "Broadband_Type": safe_value(
                row,
                "Broadband_Type"
            ),
            "QA_Status": safe_value(
                row,
                "QA_Status"
            ),
            "QA_Score": row.get(
                "QA_Score",
                ""
            ),
            "Fatal_Failure": row.get(
                "Fatal_Failure",
                ""
            ),
            "Final_QA_Result": safe_value(
                row,
                "Final_QA_Result"
            ),
            "QA_Comments": safe_value(
                row,
                "QA_Comments"
            )
        }

        for parameter_id in range(
            1,
            29
        ):

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
    # WRITE FILE
    # ------------------------------------------------------

    with pd.ExcelWriter(
        output,
        engine="xlsxwriter"
    ) as writer:

        results_df.to_excel(
            writer,
            sheet_name="QA Results",
            index=False
        )

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

        for sheet_name, dataframe in [
            (
                "QA Results",
                results_df
            ),
            (
                "Detailed QA",
                detailed_df
            )
        ]:

            worksheet = writer.sheets[
                sheet_name
            ]

            for col_num, column_name in enumerate(
                dataframe.columns
            ):

                worksheet.write(
                    0,
                    col_num,
                    column_name,
                    header_format
                )

            worksheet.freeze_panes(
                1,
                0
            )

            if not dataframe.empty:

                worksheet.autofilter(
                    0,
                    0,
                    len(dataframe),
                    len(dataframe.columns) - 1
                )

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

                    width = 30

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
# DASHBOARD HISTORY LOADER
# ==========================================================

def load_dashboard_history():

    dashboard_df, dashboard_answers = (
        sync_from_google()
    )

    if dashboard_df is None:

        st.session_state[
            "dashboard_df"
        ] = None

        st.session_state[
            "dashboard_answers"
        ] = {}

    else:

        st.session_state[
            "dashboard_df"
        ] = make_editable_dataframe(
            dashboard_df
        )

        st.session_state[
            "dashboard_answers"
        ] = dashboard_answers

    st.session_state[
        "dashboard_loaded"
    ] = True


# ==========================================================
# HEADER
# ==========================================================

st.title(
    "Sparta QA Checker"
)

st.caption(
    "Quality Assurance • Persistent Google Sheets History • Agent Performance"
)


# ==========================================================
# MAIN TABS
# ==========================================================

qa_tab, dashboard_tab = st.tabs([
    "✅ QA Checker",
    "📊 Agent Dashboard"
])


# ################################################################
# QA CHECKER TAB
# ################################################################

with qa_tab:

    # ======================================================
    # GOOGLE SHEET CONTROLS
    # ======================================================

    with st.expander(
        "☁️ Google Sheet",
        expanded=False
    ):

        col1, col2 = st.columns(2)

        with col1:

            if st.button(
                "🔄 Sync Google Sheet",
                use_container_width=True,
                key="qa_sync_button"
            ):

                try:

                    synced_df, synced_answers = (
                        sync_from_google()
                    )

                    if synced_df is None:

                        st.info(
                            "Google Sheet is currently empty."
                        )

                    else:

                        st.session_state[
                            "sales_data"
                        ] = make_editable_dataframe(
                            synced_df
                        )

                        st.session_state[
                            "qa_answers"
                        ] = synced_answers

                        st.session_state[
                            "uploaded_file_key"
                        ] = None

                        # Keep dashboard in sync too
                        st.session_state[
                            "dashboard_df"
                        ] = make_editable_dataframe(
                            synced_df
                        )

                        st.session_state[
                            "dashboard_answers"
                        ] = synced_answers

                        st.session_state[
                            "dashboard_loaded"
                        ] = True

                        st.success(
                            f"Synced "
                            f"{len(synced_df):,} "
                            "records from Google Sheets."
                        )

                        st.rerun()

                except Exception as e:

                    st.error(
                        "Google Sheet sync failed."
                    )

                    st.exception(e)

        with col2:

            st.write(
                "Google Sheets stores persistent "
                "QA records and detailed parameter answers."
            )

    # ======================================================
    # FILE UPLOAD
    # ======================================================

    uploaded_file = st.file_uploader(
        "Upload Daily Sales Excel File",
        type=[
            "xlsx",
            "xls"
        ],
        key="daily_sales_upload"
    )

    if uploaded_file is not None:

        try:

            raw_df = pd.read_excel(
                uploaded_file,
                header=None
            )

            if raw_df.shape[1] != EXPECTED_COLUMN_COUNT:

                st.error(
                    f"Unexpected file structure. "
                    f"Expected exactly "
                    f"{EXPECTED_COLUMN_COUNT} columns, "
                    f"but found "
                    f"{raw_df.shape[1]}."
                )

                st.stop()

            raw_df.columns = COLUMN_NAMES

            raw_df = raw_df.dropna(
                how="all"
            ).reset_index(
                drop=True
            )

            upload_key = (
                uploaded_file.name
                + "_"
                + str(len(raw_df))
            )

            if st.session_state.get(
                "uploaded_file_key"
            ) != upload_key:

                df_uploaded = prepare_dataframe(
                    raw_df
                )

                st.session_state[
                    "sales_data"
                ] = df_uploaded

                st.session_state[
                    "qa_answers"
                ] = {}

                st.session_state[
                    "uploaded_file_key"
                ] = upload_key

                st.success(
                    f"File uploaded successfully — "
                    f"{len(df_uploaded):,} sales loaded."
                )

        except Exception as e:

            st.error(
                "Could not read the uploaded Excel file."
            )

            st.exception(e)

    # ======================================================
    # CURRENT QA DATA
    # ======================================================

    df = st.session_state.get(
        "sales_data"
    )

    qa_answers = st.session_state.get(
        "qa_answers",
        {}
    )

    # ======================================================
    # QA WORKSPACE
    # ======================================================

    if df is not None:

        df = make_editable_dataframe(
            df
        )

        st.session_state[
            "sales_data"
        ] = df

        # ==================================================
        # TOP METRICS
        # ==================================================

        st.divider()

        st.subheader(
            "QA Dashboard"
        )

        total_sales = len(df)

        pending_count = int(
            (
                df[
                    "QA_Status"
                ]
                == "Quality Pending"
            ).sum()
        )

        completed_count = int(
            (
                df[
                    "QA_Status"
                ]
                == "Completed"
            ).sum()
        )

        approved_count = int(
            (
                df[
                    "Final_QA_Result"
                ]
                == "Approved"
            ).sum()
        )

        rejected_count = int(
            (
                df[
                    "Final_QA_Result"
                ]
                == "Rejected"
            ).sum()
        )

        col1, col2, col3, col4, col5 = (
            st.columns(5)
        )

        with col1:

            st.metric(
                "Total Sales",
                total_sales
            )

        with col2:

            st.metric(
                "Pending",
                pending_count
            )

        with col3:

            st.metric(
                "Completed",
                completed_count
            )

        with col4:

            st.metric(
                "Approved",
                approved_count
            )

        with col5:

            st.metric(
                "Rejected",
                rejected_count
            )

        # ==================================================
        # FIND SALE
        # ==================================================

        st.divider()

        st.subheader(
            "Find Sale"
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            agent_options = [
                "All"
            ] + sorted(
                df["Agent"]
                .fillna("")
                .astype(str)
                .unique()
                .tolist()
            )

            selected_agent = st.selectbox(
                "Agent",
                agent_options,
                key="find_agent"
            )

        filtered_df = df.copy()

        if selected_agent != "All":

            filtered_df = filtered_df[
                filtered_df[
                    "Agent"
                ]
                .astype(str)
                == selected_agent
            ]

        with col2:

            selected_status = st.selectbox(
                "QA Status",
                [
                    "All",
                    "Quality Pending",
                    "Completed"
                ],
                key="find_status"
            )

        if selected_status != "All":

            filtered_df = filtered_df[
                filtered_df[
                    "QA_Status"
                ]
                == selected_status
            ]

        with col3:

            selected_result = st.selectbox(
                "Final Result",
                [
                    "All"
                ] + FINAL_RESULTS,
                key="find_result"
            )

        if selected_result != "All":

            filtered_df = filtered_df[
                filtered_df[
                    "Final_QA_Result"
                ]
                == selected_result
            ]

        # ==================================================
        # SELECT SALE
        # ==================================================

        st.divider()

        st.subheader(
            "Select Sale for Quality Check"
        )

        if filtered_df.empty:

            st.warning(
                "No sales match the selected filters."
            )

        else:

            sale_options = (
                filtered_df[
                    "QA_ID"
                ]
                .astype(str)
                .tolist()
            )

            sale_display = {}

            for qa_id in sale_options:

                matching = df[
                    df[
                        "QA_ID"
                    ].astype(str)
                    == str(qa_id)
                ]

                if matching.empty:

                    sale_display[
                        qa_id
                    ] = qa_id

                else:

                    sale_row = matching.iloc[0]

                    sale_display[
                        qa_id
                    ] = (
                        f"{qa_id} — "
                        f"{safe_value(sale_row, 'Customer_Name')} — "
                        f"Agent: "
                        f"{safe_value(sale_row, 'Agent')} — "
                        f"{safe_value(sale_row, 'QA_Status')}"
                    )

            selected_qa_id = st.selectbox(
                "Sale",
                sale_options,
                format_func=lambda x:
                    sale_display.get(
                        x,
                        x
                    ),
                key="selected_sale"
            )

            # ==================================================
            # GET SELECTED SALE
            # ==================================================

            selected_rows = df[
                df[
                    "QA_ID"
                ].astype(str)
                == str(selected_qa_id)
            ]

            if not selected_rows.empty:

                sale = selected_rows.iloc[0]

                # ==============================================
                # SALE DETAILS
                # ==============================================

                st.divider()

                st.subheader(
                    "Sale Details"
                )

                col1, col2, col3, col4 = (
                    st.columns(4)
                )

                with col1:

                    st.caption("Customer")

                    st.write(
                        safe_value(
                            sale,
                            "Customer_Name"
                        )
                    )

                with col2:

                    st.caption("Phone")

                    st.write(
                        safe_value(
                            sale,
                            "Phone"
                        )
                    )

                with col3:

                    st.caption("Agent")

                    st.write(
                        safe_value(
                            sale,
                            "Agent"
                        )
                    )

                with col4:

                    st.caption("Verifier")

                    st.write(
                        safe_value(
                            sale,
                            "Verifier"
                        )
                    )

                col1, col2, col3, col4 = (
                    st.columns(4)
                )

                with col1:

                    st.caption("Sale Date")

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

                col1, col2, col3, col4 = (
                    st.columns(4)
                )

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

                col1, col2, col3, col4 = (
                    st.columns(4)
                )

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

                st.caption(
                    "Customer Address"
                )

                st.write(
                    safe_value(
                        sale,
                        "Customer_Address"
                    )
                )

                notes = safe_value(
                    sale,
                    "Additional_Notes"
                )

                if (
                    notes
                    and notes.lower() != "n/a"
                ):

                    st.caption(
                        "Additional Sale Notes"
                    )

                    st.info(
                        notes
                    )

                # ==============================================
                # PREVIOUS ANSWERS
                # ==============================================

                current_answers = (
                    qa_answers.get(
                        selected_qa_id,
                        {}
                    )
                )

                # ==============================================
                # CHECKLIST
                # ==============================================

                st.divider()

                st.subheader(
                    "Quality Checklist"
                )

                st.caption(
                    "All questions default to Yes."
                )

                with st.form(
                    key=f"qa_form_{selected_qa_id}"
                ):

                    answers = {}

                    for parameter_id, question in enumerate(
                        QA_QUESTIONS,
                        start=1
                    ):

                        question_col, answer_col = (
                            st.columns(
                                [7.5, 2.5],
                                vertical_alignment="center"
                            )
                        )

                        with question_col:

                            if (
                                parameter_id
                                in FATAL_PARAMETERS
                            ):

                                st.markdown(
                                    f"**{parameter_id}. "
                                    f"{question} ⚠️**"
                                )

                            else:

                                st.markdown(
                                    f"**{parameter_id}. "
                                    f"{question}**"
                                )

                        with answer_col:

                            previous_answer = (
                                current_answers.get(
                                    parameter_id,
                                    "Yes"
                                )
                            )

                            options = [
                                "Yes",
                                "No",
                                "N/A"
                            ]

                            if (
                                previous_answer
                                not in options
                            ):

                                previous_answer = "Yes"

                            selected_answer = st.radio(
                                f"Parameter {parameter_id}",
                                options,
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
                            ] = selected_answer

                        st.write("")

                    # ==========================================
                    # REPORT DETAILS
                    # ==========================================

                    st.divider()

                    st.subheader(
                        "QA Report Details"
                    )

                    col1, col2 = st.columns(2)

                    with col1:

                        evaluator_name = st.text_input(
                            "Evaluator Name",
                            value=safe_value(
                                sale,
                                "Evaluator_Name"
                            )
                        )

                    with col2:

                        campaign_line = st.text_input(
                            "Campaign / Line",
                            value=safe_value(
                                sale,
                                "Campaign_Line"
                            )
                        )

                    col1, col2 = st.columns(2)

                    with col1:

                        call_disposition = st.text_input(
                            "Call Disposition",
                            value=safe_value(
                                sale,
                                "Call_Disposition"
                            )
                        )

                    with col2:

                        next_review_date = st.text_input(
                            "Next Review Date",
                            value=safe_value(
                                sale,
                                "Next_Review_Date"
                            ),
                            placeholder="e.g. In 1 Week"
                        )

                    call_summary = st.text_area(
                        "Call Summary & Context",
                        value=safe_value(
                            sale,
                            "Call_Summary"
                        ),
                        height=120
                    )

                    col1, col2 = st.columns(2)

                    with col1:

                        goods = st.text_area(
                            "GOODS — Strengths",
                            value=safe_value(
                                sale,
                                "Goods"
                            ),
                            height=150
                        )

                    with col2:

                        bads = st.text_area(
                            "BADS — Errors / Areas to Improve",
                            value=safe_value(
                                sale,
                                "Bads"
                            ),
                            height=150
                        )

                    col1, col2 = st.columns(2)

                    with col1:

                        dos = st.text_area(
                            "DO'S — Recommended Behaviours",
                            value=safe_value(
                                sale,
                                "Dos"
                            ),
                            height=150
                        )

                    with col2:

                        donts = st.text_area(
                            "DON'TS — Strictly Avoid",
                            value=safe_value(
                                sale,
                                "Donts"
                            ),
                            height=150
                        )

                    actionable_coaching = st.text_area(
                        "Actionable Coaching",
                        value=safe_value(
                            sale,
                            "Actionable_Coaching"
                        ),
                        height=150
                    )

                    # ==========================================
                    # FINAL RESULT
                    # ==========================================

                    st.divider()

                    st.subheader(
                        "Final QA Decision"
                    )

                    previous_final_result = (
                        current_answers.get(
                            "final_result",
                            safe_value(
                                sale,
                                "Final_QA_Result"
                            )
                        )
                    )

                    final_result_options = [
                        "Select Final Result"
                    ] + FINAL_RESULTS

                    if (
                        previous_final_result
                        in FINAL_RESULTS
                    ):

                        final_index = (
                            final_result_options.index(
                                previous_final_result
                            )
                        )

                    else:

                        final_index = 0

                    final_result = st.selectbox(
                        "Final Result",
                        final_result_options,
                        index=final_index
                    )

                    comments = st.text_area(
                        "QA Comments",
                        value=current_answers.get(
                            "comments",
                            safe_value(
                                sale,
                                "QA_Comments"
                            )
                        ),
                        placeholder=(
                            "Enter overall QA observations..."
                        )
                    )

                    st.write("")

                    save_progress = st.form_submit_button(
                        "💾 SAVE PROGRESS",
                        use_container_width=True
                    )

                    submit_final = st.form_submit_button(
                        "✅ SUBMIT FINAL QA",
                        type="primary",
                        use_container_width=True
                    )

                # =================================================
                # SAVE / SUBMIT
                # =================================================

                if (
                    save_progress
                    or submit_final
                ):

                    answers["final_result"] = (
                        final_result
                        if final_result
                        != "Select Final Result"
                        else ""
                    )

                    answers["comments"] = comments
                    answers["evaluator_name"] = evaluator_name
                    answers["campaign_line"] = campaign_line
                    answers["call_disposition"] = call_disposition
                    answers["next_review_date"] = next_review_date
                    answers["call_summary"] = call_summary
                    answers["goods"] = goods
                    answers["bads"] = bads
                    answers["dos"] = dos
                    answers["donts"] = donts
                    answers["actionable_coaching"] = (
                        actionable_coaching
                    )

                    st.session_state[
                        "qa_answers"
                    ][selected_qa_id] = answers

                    df = make_editable_dataframe(
                        df
                    )

                    mask = (
                        df["QA_ID"].astype(str)
                        == str(selected_qa_id)
                    )

                    score = calculate_score(
                        answers
                    )

                    fatal_failure = (
                        has_fatal_failure(
                            answers
                        )
                    )

                    # =============================================
                    # SAVE PROGRESS
                    # =============================================

                    if save_progress:

                        df.loc[
                            mask,
                            "QA_Score"
                        ] = score

                        df.loc[
                            mask,
                            "Fatal_Failure"
                        ] = fatal_failure

                        df.loc[
                            mask,
                            "QA_Comments"
                        ] = comments

                        df.loc[
                            mask,
                            "QA_Status"
                        ] = "Quality Pending"

                        report_fields = {
                            "Evaluator_Name": evaluator_name,
                            "Campaign_Line": campaign_line,
                            "Call_Disposition": call_disposition,
                            "Next_Review_Date": next_review_date,
                            "Call_Summary": call_summary,
                            "Goods": goods,
                            "Bads": bads,
                            "Dos": dos,
                            "Donts": donts,
                            "Actionable_Coaching": actionable_coaching,
                            "Last_Updated": current_timestamp()
                        }

                        for column, value in report_fields.items():

                            df.loc[
                                mask,
                                column
                            ] = value

                        st.session_state[
                            "sales_data"
                        ] = make_editable_dataframe(
                            df
                        )

                        try:

                            save_sale_to_google(
                                df[
                                    mask
                                ].iloc[0],
                                answers
                            )

                            update_agent_summary(
                                df
                            )

                            st.success(
                                "Progress saved successfully "
                                "to Google Sheets."
                            )

                        except Exception as e:

                            st.warning(
                                "Progress was saved in the current "
                                "session, but Google Sheet saving failed."
                            )

                            st.exception(e)

                    # =============================================
                    # FINAL SUBMISSION
                    # =============================================

                    if submit_final:

                        if (
                            final_result
                            == "Select Final Result"
                        ):

                            st.error(
                                "Please select a Final QA Result "
                                "before submitting."
                            )

                        else:

                            df.loc[
                                mask,
                                "QA_Status"
                            ] = "Completed"

                            df.loc[
                                mask,
                                "QA_Score"
                            ] = score

                            df.loc[
                                mask,
                                "Fatal_Failure"
                            ] = fatal_failure

                            df.loc[
                                mask,
                                "Final_QA_Result"
                            ] = final_result

                            df.loc[
                                mask,
                                "QA_Comments"
                            ] = comments

                            report_fields = {
                                "Evaluator_Name": evaluator_name,
                                "Campaign_Line": campaign_line,
                                "Call_Disposition": call_disposition,
                                "Next_Review_Date": next_review_date,
                                "Call_Summary": call_summary,
                                "Goods": goods,
                                "Bads": bads,
                                "Dos": dos,
                                "Donts": donts,
                                "Actionable_Coaching": actionable_coaching,
                                "Last_Updated": current_timestamp()
                            }

                            for column, value in report_fields.items():

                                df.loc[
                                    mask,
                                    column
                                ] = value

                            # --------------------------------------
                            # Save QA data
                            # --------------------------------------

                            st.session_state[
                                "sales_data"
                            ] = make_editable_dataframe(
                                df
                            )

                            google_saved = False

                            try:

                                save_sale_to_google(
                                    df[
                                        mask
                                    ].iloc[0],
                                    answers
                                )

                                update_agent_summary(
                                    df
                                )

                                google_saved = True

                            except Exception as e:

                                st.warning(
                                    "QA was completed in the app, "
                                    "but the Google Sheet save failed."
                                )

                                st.exception(e)

                            # --------------------------------------
                            # SAFE dashboard update
                            # --------------------------------------
                            #
                            # THIS IS THE FIX FOR THE ERROR YOU GOT.
                            #
                            # Convert the ENTIRE dataframe to object
                            # before assigning updated values.
                            # --------------------------------------

                            dashboard_df_existing = (
                                st.session_state.get(
                                    "dashboard_df"
                                )
                            )

                            if (
                                dashboard_df_existing
                                is not None
                            ):

                                dashboard_df_existing = (
                                    dashboard_df_existing
                                    .copy()
                                )

                                # CRITICAL FIX
                                dashboard_df_existing = (
                                    dashboard_df_existing
                                    .astype(object)
                                )

                                # Make sure all sale columns exist
                                for column in df.columns:

                                    if (
                                        column
                                        not in dashboard_df_existing.columns
                                    ):

                                        dashboard_df_existing[
                                            column
                                        ] = ""

                                existing_mask = (
                                    dashboard_df_existing[
                                        "QA_ID"
                                    ]
                                    .astype(str)
                                    == str(
                                        selected_qa_id
                                    )
                                )

                                updated_sale = (
                                    df[
                                        mask
                                    ].iloc[0]
                                )

                                if existing_mask.any():

                                    # ----------------------------------
                                    # Update existing record using
                                    # a single row replacement.
                                    #
                                    # This is safer than repeatedly
                                    # assigning individual values into
                                    # Arrow string columns.
                                    # ----------------------------------

                                    matching_indices = (
                                        dashboard_df_existing.index[
                                            existing_mask
                                        ]
                                    )

                                    update_values = {}

                                    for column in dashboard_df_existing.columns:

                                        if (
                                            column
                                            in updated_sale.index
                                        ):

                                            value = (
                                                updated_sale[
                                                    column
                                                ]
                                            )

                                            if pd.isna(
                                                value
                                            ):

                                                value = ""

                                            update_values[
                                                column
                                            ] = value

                                    for idx in matching_indices:

                                        for column, value in update_values.items():

                                            dashboard_df_existing.at[
                                                idx,
                                                column
                                            ] = value

                                else:

                                    # ----------------------------------
                                    # New row
                                    # ----------------------------------

                                    new_row_data = {}

                                    for column in dashboard_df_existing.columns:

                                        if (
                                            column
                                            in updated_sale.index
                                        ):

                                            value = (
                                                updated_sale[
                                                    column
                                                ]
                                            )

                                            if pd.isna(
                                                value
                                            ):

                                                value = ""

                                            new_row_data[
                                                column
                                            ] = value

                                        else:

                                            new_row_data[
                                                column
                                            ] = ""

                                    new_row = pd.DataFrame([
                                        new_row_data
                                    ])

                                    new_row = (
                                        new_row
                                        .astype(object)
                                    )

                                    dashboard_df_existing = (
                                        pd.concat(
                                            [
                                                dashboard_df_existing,
                                                new_row
                                            ],
                                            ignore_index=True
                                        )
                                    )

                                # ----------------------------------
                                # Final safety conversion
                                # ----------------------------------

                                dashboard_df_existing = (
                                    dashboard_df_existing
                                    .astype(object)
                                )

                                st.session_state[
                                    "dashboard_df"
                                ] = (
                                    dashboard_df_existing
                                )

                                st.session_state[
                                    "dashboard_answers"
                                ][
                                    selected_qa_id
                                ] = answers

                            # --------------------------------------
                            # Final result display
                            # --------------------------------------

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

                            elif (
                                final_result
                                == "Reworked Required"
                            ):

                                st.warning(
                                    "SALE QA COMPLETED — REWORK REQUIRED"
                                )

                            elif final_result == "Hold":

                                st.info(
                                    "SALE QA COMPLETED — ON HOLD"
                                )

                            col1, col2, col3 = (
                                st.columns(3)
                            )

                            with col1:

                                st.metric(
                                    "Quality Score",
                                    f"{score:.2f}%"
                                )

                            with col2:

                                st.metric(
                                    "Fatal Failure",
                                    (
                                        "YES"
                                        if fatal_failure
                                        else "NO"
                                    )
                                )

                            with col3:

                                st.metric(
                                    "Final QA Result",
                                    final_result
                                )

                            if google_saved:

                                st.success(
                                    "✓ QA result saved to Google Sheets."
                                )

                # ==============================================
                # CURRENT RESULTS
                # ==============================================

                st.divider()

                st.subheader(
                    "Current QA Results"
                )

                results_table_columns = [
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

                current_results_df = df[
                    results_table_columns
                ].copy()

                st.dataframe(
                    current_results_df,
                    use_container_width=True,
                    hide_index=True
                )

                # ==============================================
                # EXCEL EXPORT
                # ==============================================

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
                    use_container_width=True,
                    key="qa_excel_download"
                )

    else:

        st.info(
            "Upload a daily sales Excel file above "
            "or use Google Sheet Sync to load existing QA records."
        )


# ################################################################
# AGENT DASHBOARD TAB
# ################################################################

with dashboard_tab:

    st.subheader(
        "📊 Agent Performance Dashboard"
    )

    st.caption(
        "Historical QA performance from the persistent Google Sheet."
    )

    # ======================================================
    # LOAD HISTORY
    # ======================================================

    if not st.session_state[
        "dashboard_loaded"
    ]:

        try:

            with st.spinner(
                "Loading historical QA data..."
            ):

                load_dashboard_history()

        except Exception as e:

            st.error(
                "Could not load historical QA data."
            )

            st.exception(e)

    # ======================================================
    # REFRESH
    # ======================================================

    col1, col2 = st.columns(
        [1, 4]
    )

    with col1:

        refresh_dashboard = st.button(
            "🔄 Refresh Historical Data",
            use_container_width=True,
            key="refresh_dashboard"
        )

    with col2:

        st.caption(
            "Refresh to retrieve the latest completed QA records from Google Sheets."
        )

    if refresh_dashboard:

        try:

            with st.spinner(
                "Refreshing historical QA data..."
            ):

                load_dashboard_history()

            st.success(
                "Dashboard data refreshed."
            )

        except Exception as e:

            st.error(
                "Dashboard refresh failed."
            )

            st.exception(e)

    # ======================================================
    # GET DASHBOARD DATA
    # ======================================================

    dashboard_df = st.session_state.get(
        "dashboard_df"
    )

    dashboard_answers = st.session_state.get(
        "dashboard_answers",
        {}
    )

    # ======================================================
    # NO DATA
    # ======================================================

    if dashboard_df is None:

        st.info(
            "No historical QA records are currently available."
        )

    elif dashboard_df.empty:

        st.info(
            "Google Sheets does not contain any QA records yet."
        )

    else:

        # Safety conversion
        dashboard_df = (
            dashboard_df
            .copy()
            .astype(object)
        )

        # ==================================================
        # COMPLETED ONLY
        # ==================================================

        completed_df = dashboard_df[
            dashboard_df[
                "QA_Status"
            ]
            == "Completed"
        ].copy()

        if completed_df.empty:

            st.info(
                "There are no completed QA records yet."
            )

        else:

            # ==============================================
            # DATE FILTER
            # ==============================================

            parsed_dates = pd.to_datetime(
                completed_df[
                    "Sale_Date"
                ],
                errors="coerce",
                dayfirst=True
            )

            valid_dates = parsed_dates.dropna()

            if valid_dates.empty:

                dashboard_filtered = (
                    completed_df.copy()
                )

            else:

                min_date = (
                    valid_dates
                    .min()
                    .date()
                )

                max_date = (
                    valid_dates
                    .max()
                    .date()
                )

                st.markdown(
                    "### Filters"
                )

                col1, col2 = st.columns(2)

                with col1:

                    dashboard_start = st.date_input(
                        "From Date",
                        value=min_date,
                        min_value=min_date,
                        max_value=max_date,
                        key="agent_dashboard_from"
                    )

                with col2:

                    dashboard_end = st.date_input(
                        "To Date",
                        value=max_date,
                        min_value=min_date,
                        max_value=max_date,
                        key="agent_dashboard_to"
                    )

                if (
                    dashboard_start
                    > dashboard_end
                ):

                    st.error(
                        "From Date cannot be after To Date."
                    )

                    dashboard_filtered = (
                        completed_df.iloc[
                            0:0
                        ].copy()
                    )

                else:

                    dashboard_dates = (
                        pd.to_datetime(
                            completed_df[
                                "Sale_Date"
                            ],
                            errors="coerce",
                            dayfirst=True
                        )
                        .dt.date
                    )

                    dashboard_filtered = (
                        completed_df[
                            (
                                dashboard_dates
                                >= dashboard_start
                            )
                            &
                            (
                                dashboard_dates
                                <= dashboard_end
                            )
                        ].copy()
                    )

            # ==============================================
            # AGENT FILTER
            # ==============================================

            if not dashboard_filtered.empty:

                agent_options = [
                    "All"
                ] + sorted(
                    dashboard_filtered[
                        "Agent"
                    ]
                    .fillna("")
                    .astype(str)
                    .unique()
                    .tolist()
                )

                dashboard_agent = st.selectbox(
                    "Agent",
                    agent_options,
                    key="agent_dashboard_agent"
                )

                if (
                    dashboard_agent
                    != "All"
                ):

                    dashboard_filtered = (
                        dashboard_filtered[
                            dashboard_filtered[
                                "Agent"
                            ].astype(str)
                            == dashboard_agent
                        ].copy()
                    )

            if dashboard_filtered.empty:

                st.info(
                    "No completed QA records match the selected filters."
                )

            else:

                # ==========================================
                # KPI METRICS
                # ==========================================

                st.divider()

                dashboard_scores = pd.to_numeric(
                    dashboard_filtered[
                        "QA_Score"
                    ],
                    errors="coerce"
                )

                average_score = (
                    dashboard_scores.mean()
                    if dashboard_scores.notna().any()
                    else 0
                )

                approved_count = int(
                    (
                        dashboard_filtered[
                            "Final_QA_Result"
                        ]
                        == "Approved"
                    ).sum()
                )

                rejected_count = int(
                    (
                        dashboard_filtered[
                            "Final_QA_Result"
                        ]
                        == "Rejected"
                    ).sum()
                )

                cancelled_count = int(
                    (
                        dashboard_filtered[
                            "Final_QA_Result"
                        ]
                        == "Cancelled"
                    ).sum()
                )

                reworked_count = int(
                    (
                        dashboard_filtered[
                            "Final_QA_Result"
                        ]
                        == "Reworked Required"
                    ).sum()
                )

                hold_count = int(
                    (
                        dashboard_filtered[
                            "Final_QA_Result"
                        ]
                        == "Hold"
                    ).sum()
                )

                fatal_count = int(
                    dashboard_filtered[
                        "Fatal_Failure"
                    ]
                    .fillna(False)
                    .astype(bool)
                    .sum()
                )

                col1, col2, col3, col4, col5 = (
                    st.columns(5)
                )

                with col1:

                    st.metric(
                        "Sales Checked",
                        len(dashboard_filtered)
                    )

                with col2:

                    st.metric(
                        "Average Score",
                        f"{average_score:.2f}%"
                    )

                with col3:

                    st.metric(
                        "Approved",
                        approved_count
                    )

                with col4:

                    st.metric(
                        "Rejected",
                        rejected_count
                    )

                with col5:

                    st.metric(
                        "Fatal Failures",
                        fatal_count
                    )

                # ==========================================
                # OUTCOME BREAKDOWN
                # ==========================================

                st.divider()

                st.markdown(
                    "### QA Outcome Breakdown"
                )

                outcome_df = pd.DataFrame([
                    {
                        "Final Result": "Approved",
                        "Count": approved_count
                    },
                    {
                        "Final Result": "Rejected",
                        "Count": rejected_count
                    },
                    {
                        "Final Result": "Cancelled",
                        "Count": cancelled_count
                    },
                    {
                        "Final Result": "Reworked Required",
                        "Count": reworked_count
                    },
                    {
                        "Final Result": "Hold",
                        "Count": hold_count
                    }
                ])

                st.dataframe(
                    outcome_df,
                    use_container_width=True,
                    hide_index=True
                )

                # ==========================================
                # AGENT RANKING
                # ==========================================

                st.divider()

                st.markdown(
                    "### Agent Performance Ranking"
                )

                ranking_rows = []

                for agent, group in dashboard_filtered.groupby(
                    "Agent",
                    dropna=False
                ):

                    scores = pd.to_numeric(
                        group[
                            "QA_Score"
                        ],
                        errors="coerce"
                    )

                    agent_average = (
                        scores.mean()
                        if scores.notna().any()
                        else 0
                    )

                    fatal_series = (
                        group[
                            "Fatal_Failure"
                        ]
                        .fillna(False)
                        .astype(bool)
                    )

                    ranking_rows.append({
                        "Agent": str(agent),
                        "Sales Checked": len(group),
                        "Average QA Score": round(
                            agent_average,
                            2
                        ),
                        "Approved": int(
                            (
                                group[
                                    "Final_QA_Result"
                                ]
                                == "Approved"
                            ).sum()
                        ),
                        "Rejected": int(
                            (
                                group[
                                    "Final_QA_Result"
                                ]
                                == "Rejected"
                            ).sum()
                        ),
                        "Cancelled": int(
                            (
                                group[
                                    "Final_QA_Result"
                                ]
                                == "Cancelled"
                            ).sum()
                        ),
                        "Reworked": int(
                            (
                                group[
                                    "Final_QA_Result"
                                ]
                                == "Reworked Required"
                            ).sum()
                        ),
                        "Hold": int(
                            (
                                group[
                                    "Final_QA_Result"
                                ]
                                == "Hold"
                            ).sum()
                        ),
                        "Fatal Failures": int(
                            fatal_series.sum()
                        )
                    })

                ranking_df = pd.DataFrame(
                    ranking_rows
                )

                if not ranking_df.empty:

                    ranking_df = (
                        ranking_df
                        .sort_values(
                            "Average QA Score",
                            ascending=False
                        )
                        .reset_index(
                            drop=True
                        )
                    )

                    ranking_df.insert(
                        0,
                        "Rank",
                        range(
                            1,
                            len(ranking_df) + 1
                        )
                    )

                    st.dataframe(
                        ranking_df,
                        use_container_width=True,
                        hide_index=True
                    )

                # ==========================================
                # PARAMETER PERFORMANCE
                # ==========================================

                st.divider()

                st.markdown(
                    "### 28-Parameter Performance"
                )

                st.caption(
                    "Yes % is calculated against applicable checks only. N/A is excluded."
                )

                parameter_df = (
                    get_parameter_performance(
                        dashboard_filtered,
                        dashboard_answers
                    )
                )

                parameter_display = (
                    parameter_df[
                        [
                            "Parameter",
                            "Question",
                            "Yes",
                            "No",
                            "N/A",
                            "Applicable",
                            "Yes %"
                        ]
                    ]
                    .sort_values(
                        "Yes %"
                    )
                )

                st.dataframe(
                    parameter_display,
                    use_container_width=True,
                    hide_index=True
                )

                # ==========================================
                # WEAKEST PARAMETERS
                # ==========================================

                st.divider()

                st.markdown(
                    "### ⚠️ Areas Needing Most Attention"
                )

                weakest = (
                    parameter_df[
                        parameter_df[
                            "Applicable"
                        ] > 0
                    ]
                    .sort_values(
                        "Yes %"
                    )
                    .head(5)
                )

                if weakest.empty:

                    st.info(
                        "No parameter data is available."
                    )

                else:

                    for _, item in weakest.iterrows():

                        st.write(
                            f"**Parameter "
                            f"{int(item['Parameter'])} — "
                            f"{item['Yes %']:.2f}% Yes**"
                        )

                        st.caption(
                            item["Question"]
                        )

                        st.write(
                            f"Yes: {int(item['Yes'])}  |  "
                            f"No: {int(item['No'])}  |  "
                            f"N/A: {int(item['N/A'])}"
                        )

                        st.write("")

                # ==========================================
                # AGENT PARAMETER BREAKDOWN
                # ==========================================

                st.divider()

                st.markdown(
                    "### Agent Parameter Breakdown"
                )

                breakdown_agent_options = [
                    "All"
                ] + sorted(
                    dashboard_filtered[
                        "Agent"
                    ]
                    .fillna("")
                    .astype(str)
                    .unique()
                    .tolist()
                )

                breakdown_agent = st.selectbox(
                    "Select Agent",
                    breakdown_agent_options,
                    key="parameter_breakdown_agent"
                )

                breakdown_df = (
                    dashboard_filtered.copy()
                )

                if (
                    breakdown_agent
                    != "All"
                ):

                    breakdown_df = (
                        breakdown_df[
                            breakdown_df[
                                "Agent"
                            ].astype(str)
                            == breakdown_agent
                        ].copy()
                    )

                breakdown_parameter_df = (
                    get_parameter_performance(
                        breakdown_df,
                        dashboard_answers
                    )
                )

                st.dataframe(
                    breakdown_parameter_df[
                        [
                            "Parameter",
                            "Question",
                            "Yes",
                            "No",
                            "N/A",
                            "Applicable",
                            "Yes %"
                        ]
                    ].sort_values(
                        "Yes %"
                    ),
                    use_container_width=True,
                    hide_index=True
                )

                # ==========================================
                # SCORE DISTRIBUTION
                # ==========================================

                st.divider()

                st.markdown(
                    "### QA Score Distribution"
                )

                score_distribution = (
                    pd.to_numeric(
                        dashboard_filtered[
                            "QA_Score"
                        ],
                        errors="coerce"
                    )
                    .dropna()
                )

                if not score_distribution.empty:

                    bins = [
                        0,
                        50,
                        60,
                        70,
                        80,
                        90,
                        100.000001
                    ]

                    labels = [
                        "0–49%",
                        "50–59%",
                        "60–69%",
                        "70–79%",
                        "80–89%",
                        "90–100%"
                    ]

                    score_buckets = pd.cut(
                        score_distribution,
                        bins=bins,
                        labels=labels,
                        include_lowest=True
                    )

                    score_distribution_df = (
                        score_buckets
                        .value_counts()
                        .reindex(
                            labels,
                            fill_value=0
                        )
                        .rename_axis(
                            "Score Range"
                        )
                        .reset_index(
                            name="Sales"
                        )
                    )

                    st.dataframe(
                        score_distribution_df,
                        use_container_width=True,
                        hide_index=True
                    )
