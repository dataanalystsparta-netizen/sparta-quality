import streamlit as st
import pandas as pd
import gspread
import hashlib

from io import BytesIO
from datetime import datetime
from xml.sax.saxutils import escape

from google.oauth2.service_account import Credentials

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
    PageBreak,
)


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
# INPUT FILE STRUCTURE - EXACT 40 COLUMNS
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
    "Customer_Address",       # 21
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

# ----------------------------------------------------------
# Google row caches
# ----------------------------------------------------------

if "google_record_rows" not in st.session_state:
    st.session_state["google_record_rows"] = {}

if "google_answer_rows" not in st.session_state:
    st.session_state["google_answer_rows"] = {}

if "google_next_record_row" not in st.session_state:
    st.session_state["google_next_record_row"] = None

if "google_next_answer_row" not in st.session_state:
    st.session_state["google_next_answer_row"] = None


# ==========================================================
# BASIC HELPERS
# ==========================================================

def safe_value(row, column_name):

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

    if df is None:
        return None

    return df.copy().astype(object)


def safe_filename_part(value):

    value = str(value or "").strip()

    if not value:
        value = "Unknown"

    invalid_chars = [
        "<",
        ">",
        ":",
        '"',
        "/",
        "\\",
        "|",
        "?",
        "*"
    ]

    for char in invalid_chars:
        value = value.replace(
            char,
            "_"
        )

    value = " ".join(
        value.split()
    )

    return value[:100]


def sale_report_filename(row):

    agent = safe_filename_part(
        safe_value(
            row,
            "Agent"
        )
    )

    customer = safe_filename_part(
        safe_value(
            row,
            "Customer_Name"
        )
    )

    sale_date = safe_filename_part(
        safe_value(
            row,
            "Sale_Date"
        )
    )

    if not sale_date:
        sale_date = datetime.now().strftime(
            "%d-%m-%Y"
        )

    return (
        f"{agent}_"
        f"{customer}_"
        f"{sale_date}"
    )


# ==========================================================
# QA ID
# ==========================================================

def generate_qa_id(row):

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

    df = df.copy()

    for column in COLUMN_NAMES:

        if column not in df.columns:
            df[column] = ""

    if "QA_ID" not in df.columns:

        df["QA_ID"] = df.apply(
            generate_qa_id,
            axis=1
        )

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
# GOOGLE CLIENT
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


# ==========================================================
# GOOGLE WORKSHEET BUNDLE
# ==========================================================

@st.cache_resource
def get_google_sheet_bundle():

    client = get_google_client()

    spreadsheet = client.open_by_key(
        GOOGLE_SHEET_ID
    )

    # One metadata call
    existing_worksheets = (
        spreadsheet.worksheets()
    )

    worksheets = {
        ws.title: ws
        for ws in existing_worksheets
    }

    # ------------------------------------------------------
    # QA Records
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

    if QA_RECORDS_SHEET not in worksheets:

        worksheet = spreadsheet.add_worksheet(
            title=QA_RECORDS_SHEET,
            rows=1000,
            cols=len(records_headers) + 5
        )

        worksheet.update(
            "A1",
            [records_headers]
        )

        worksheets[
            QA_RECORDS_SHEET
        ] = worksheet

    # ------------------------------------------------------
    # QA Answers
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

    if QA_ANSWERS_SHEET not in worksheets:

        worksheet = spreadsheet.add_worksheet(
            title=QA_ANSWERS_SHEET,
            rows=1000,
            cols=len(answer_headers) + 5
        )

        worksheet.update(
            "A1",
            [answer_headers]
        )

        worksheets[
            QA_ANSWERS_SHEET
        ] = worksheet

    # ------------------------------------------------------
    # QA Parameters
    # ------------------------------------------------------

    parameter_headers = [
        "Parameter_ID",
        "Question",
        "Fatal",
        "Weight",
        "Active"
    ]

    if QA_PARAMETERS_SHEET not in worksheets:

        worksheet = spreadsheet.add_worksheet(
            title=QA_PARAMETERS_SHEET,
            rows=100,
            cols=10
        )

        worksheet.update(
            "A1",
            [parameter_headers]
        )

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

        worksheet.append_rows(
            parameter_rows,
            value_input_option="USER_ENTERED"
        )

        worksheets[
            QA_PARAMETERS_SHEET
        ] = worksheet

    # ------------------------------------------------------
    # Agent Summary
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

    if AGENT_SUMMARY_SHEET not in worksheets:

        worksheet = spreadsheet.add_worksheet(
            title=AGENT_SUMMARY_SHEET,
            rows=1000,
            cols=15
        )

        worksheet.update(
            "A1",
            [summary_headers]
        )

        worksheets[
            AGENT_SUMMARY_SHEET
        ] = worksheet

    return {
        "spreadsheet": spreadsheet,
        "records": worksheets[
            QA_RECORDS_SHEET
        ],
        "answers": worksheets[
            QA_ANSWERS_SHEET
        ],
        "parameters": worksheets[
            QA_PARAMETERS_SHEET
        ],
        "summary": worksheets[
            AGENT_SUMMARY_SHEET
        ]
    }


# ==========================================================
# INITIALISE ALIAS
# ==========================================================

def initialise_google_sheets():

    return get_google_sheet_bundle()


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
            chr(65 + remainder)
            + result
        )

    return result


# ==========================================================
# SALE ROW → GOOGLE
# ==========================================================

def row_to_google_values(row):

    values = []

    for column in COLUMN_NAMES:

        values.append(
            safe_value(
                row,
                column
            )
        )

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
# ANSWERS → GOOGLE
# ==========================================================

def answers_to_google_values(
    qa_id,
    answers
):

    values = [
        qa_id
    ]

    for parameter_id in range(
        1,
        29
    ):

        values.append(
            answers.get(
                parameter_id,
                "Yes"
            )
        )

    values.append(
        current_timestamp()
    )

    return values


# ==========================================================
# BUILD GOOGLE ROW CACHE
# ==========================================================

def build_google_row_caches():

    sheets = get_google_sheet_bundle()

    records_ws = sheets[
        "records"
    ]

    answers_ws = sheets[
        "answers"
    ]

    record_values = (
        records_ws.get_all_records()
    )

    answer_values = (
        answers_ws.get_all_records()
    )

    record_rows = {}
    answer_rows = {}

    for index, record in enumerate(
        record_values,
        start=2
    ):

        qa_id = str(
            record.get(
                "QA_ID",
                ""
            )
        ).strip()

        if qa_id:

            record_rows[
                qa_id
            ] = index

    for index, record in enumerate(
        answer_values,
        start=2
    ):

        qa_id = str(
            record.get(
                "QA_ID",
                ""
            )
        ).strip()

        if qa_id:

            answer_rows[
                qa_id
            ] = index

    st.session_state[
        "google_record_rows"
    ] = record_rows

    st.session_state[
        "google_answer_rows"
    ] = answer_rows

    st.session_state[
        "google_next_record_row"
    ] = len(record_values) + 2

    st.session_state[
        "google_next_answer_row"
    ] = len(answer_values) + 2


# ==========================================================
# SAVE SALE TO GOOGLE
# NO FULL SHEET READ
# ==========================================================

def save_sale_to_google(
    sale_row,
    answers
):

    sheets = get_google_sheet_bundle()

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

    # If caches don't exist yet, do the initial read once.
    if (
        not st.session_state[
            "google_record_rows"
        ]
        and st.session_state.get(
            "google_next_record_row"
        ) is None
    ):

        build_google_row_caches()

    record_cache = st.session_state[
        "google_record_rows"
    ]

    answer_cache = st.session_state[
        "google_answer_rows"
    ]

    # ======================================================
    # QA RECORD
    # ======================================================

    record_values = row_to_google_values(
        sale_row
    )

    existing_record_row = (
        record_cache.get(
            qa_id
        )
    )

    if existing_record_row:

        last_column = column_letter(
            len(record_values)
        )

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

        new_row = (
            st.session_state.get(
                "google_next_record_row"
            )
            or 2
        )

        record_cache[
            qa_id
        ] = new_row

        st.session_state[
            "google_next_record_row"
        ] = new_row + 1

    # ======================================================
    # QA ANSWERS
    # ======================================================

    answer_values = answers_to_google_values(
        qa_id,
        answers
    )

    existing_answer_row = (
        answer_cache.get(
            qa_id
        )
    )

    if existing_answer_row:

        last_column = column_letter(
            len(answer_values)
        )

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

        new_row = (
            st.session_state.get(
                "google_next_answer_row"
            )
            or 2
        )

        answer_cache[
            qa_id
        ] = new_row

        st.session_state[
            "google_next_answer_row"
        ] = new_row + 1


# ==========================================================
# GOOGLE → APP
# ==========================================================

def sync_from_google():

    sheets = get_google_sheet_bundle()

    records = (
        sheets[
            "records"
        ].get_all_records()
    )

    answer_records = (
        sheets[
            "answers"
        ].get_all_records()
    )

    # ------------------------------------------------------
    # Empty sheet
    # ------------------------------------------------------

    if not records:

        st.session_state[
            "google_record_rows"
        ] = {}

        st.session_state[
            "google_next_record_row"
        ] = 2

        answer_rows = {}

        for index, record in enumerate(
            answer_records,
            start=2
        ):

            qa_id = str(
                record.get(
                    "QA_ID",
                    ""
                )
            ).strip()

            if qa_id:

                answer_rows[
                    qa_id
                ] = index

        st.session_state[
            "google_answer_rows"
        ] = answer_rows

        st.session_state[
            "google_next_answer_row"
        ] = len(
            answer_records
        ) + 2

        return None, {}

    records_df = pd.DataFrame(
        records
    )

    records_df = prepare_dataframe(
        records_df
    )

    # ------------------------------------------------------
    # Score
    # ------------------------------------------------------

    records_df[
        "QA_Score"
    ] = pd.to_numeric(
        records_df[
            "QA_Score"
        ],
        errors="coerce"
    ).astype(object)

    # ------------------------------------------------------
    # Fatal
    # ------------------------------------------------------

    records_df[
        "Fatal_Failure"
    ] = (
        records_df[
            "Fatal_Failure"
        ]
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
    # Row caches
    # ------------------------------------------------------

    record_rows = {}
    answer_rows = {}

    for index, record in enumerate(
        records,
        start=2
    ):

        qa_id = str(
            record.get(
                "QA_ID",
                ""
            )
        ).strip()

        if qa_id:

            record_rows[
                qa_id
            ] = index

    for index, record in enumerate(
        answer_records,
        start=2
    ):

        qa_id = str(
            record.get(
                "QA_ID",
                ""
            )
        ).strip()

        if qa_id:

            answer_rows[
                qa_id
            ] = index

    st.session_state[
        "google_record_rows"
    ] = record_rows

    st.session_state[
        "google_answer_rows"
    ] = answer_rows

    st.session_state[
        "google_next_record_row"
    ] = len(records) + 2

    st.session_state[
        "google_next_answer_row"
    ] = len(answer_records) + 2

    # ------------------------------------------------------
    # Answers
    # ------------------------------------------------------

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
        # Report information from QA Records
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
# CREATE INDIVIDUAL SALE EXCEL
# ==========================================================

def create_individual_excel(
    sale,
    answers
):
    """
    Creates a beautifully formatted single-sale QA report.
    """

    output = BytesIO()

    base_name = sale_report_filename(
        sale
    )

    # ------------------------------------------------------
    # Main report values
    # ------------------------------------------------------

    report_values = {
        "Agent Name": safe_value(
            sale,
            "Agent"
        ),
        "Sale Date": safe_value(
            sale,
            "Sale_Date"
        ),
        "Campaign / Line": safe_value(
            sale,
            "Campaign_Line"
        ),
        "Evaluator Name": safe_value(
            sale,
            "Evaluator_Name"
        ),
        "Customer Name": safe_value(
            sale,
            "Customer_Name"
        ),
        "Call Disposition": safe_value(
            sale,
            "Call_Disposition"
        ),
        "CLI": safe_value(
            sale,
            "Phone"
        ),
        "Next Review Date": safe_value(
            sale,
            "Next_Review_Date"
        )
    }

    call_summary = safe_value(
        sale,
        "Call_Summary"
    )

    goods = safe_value(
        sale,
        "Goods"
    )

    bads = safe_value(
        sale,
        "Bads"
    )

    dos = safe_value(
        sale,
        "Dos"
    )

    donts = safe_value(
        sale,
        "Donts"
    )

    coaching = safe_value(
        sale,
        "Actionable_Coaching"
    )

    # ------------------------------------------------------
    # Workbook
    # ------------------------------------------------------

    with pd.ExcelWriter(
        output,
        engine="xlsxwriter"
    ) as writer:

        workbook = writer.book

        worksheet = workbook.add_worksheet(
            "Call Quality Report"
        )

        # --------------------------------------------------
        # Palette
        # --------------------------------------------------

        navy = "#17365D"
        blue = "#2F75B5"
        light_blue = "#D9EAF7"
        light_grey = "#F3F6F9"
        medium_grey = "#D9E1F2"
        dark_grey = "#404040"
        green = "#E2F0D9"
        red = "#FCE4D6"
        gold = "#FFF2CC"
        white = "#FFFFFF"

        # --------------------------------------------------
        # Formats
        # --------------------------------------------------

        title_format = workbook.add_format({
            "bold": True,
            "font_size": 20,
            "font_color": white,
            "bg_color": navy,
            "align": "center",
            "valign": "vcenter"
        })

        subtitle_format = workbook.add_format({
            "italic": True,
            "font_size": 10,
            "font_color": dark_grey,
            "align": "center",
            "valign": "vcenter"
        })

        label_format = workbook.add_format({
            "bold": True,
            "font_color": navy,
            "bg_color": light_blue,
            "border": 1,
            "border_color": medium_grey,
            "valign": "top"
        })

        value_format = workbook.add_format({
            "font_color": dark_grey,
            "bg_color": white,
            "border": 1,
            "border_color": medium_grey,
            "text_wrap": True,
            "valign": "top"
        })

        section_format = workbook.add_format({
            "bold": True,
            "font_size": 13,
            "font_color": white,
            "bg_color": blue,
            "border": 1,
            "border_color": blue,
            "align": "left",
            "valign": "vcenter"
        })

        body_format = workbook.add_format({
            "font_color": dark_grey,
            "bg_color": white,
            "border": 1,
            "border_color": medium_grey,
            "text_wrap": True,
            "valign": "top"
        })

        goods_header_format = workbook.add_format({
            "bold": True,
            "font_color": "#2F6B2F",
            "bg_color": green,
            "border": 1,
            "border_color": medium_grey,
            "align": "left"
        })

        bads_header_format = workbook.add_format({
            "bold": True,
            "font_color": "#9C0006",
            "bg_color": red,
            "border": 1,
            "border_color": medium_grey,
            "align": "left"
        })

        dos_header_format = workbook.add_format({
            "bold": True,
            "font_color": "#2F6B2F",
            "bg_color": green,
            "border": 1,
            "border_color": medium_grey,
            "align": "left"
        })

        donts_header_format = workbook.add_format({
            "bold": True,
            "font_color": "#9C0006",
            "bg_color": red,
            "border": 1,
            "border_color": medium_grey,
            "align": "left"
        })

        small_note_format = workbook.add_format({
            "font_size": 9,
            "font_color": dark_grey,
            "italic": True
        })

        # --------------------------------------------------
        # Column widths
        # --------------------------------------------------

        worksheet.set_column(
            "A:A",
            23
        )

        worksheet.set_column(
            "B:B",
            34
        )

        worksheet.set_column(
            "C:C",
            23
        )

        worksheet.set_column(
            "D:D",
            34
        )

        # --------------------------------------------------
        # Page / print settings
        # --------------------------------------------------

        worksheet.hide_gridlines(2)

        worksheet.set_landscape()

        worksheet.fit_to_pages(
            1,
            0
        )

        worksheet.set_margins(
            left=0.35,
            right=0.35,
            top=0.5,
            bottom=0.5
        )

        worksheet.set_header(
            "&C&\"Calibri,Bold\"Sparta Telecom - Call Quality Evaluation"
        )

        worksheet.set_footer(
            "&LConfidential QA Report&CPage &P of &N&R"
        )

        # --------------------------------------------------
        # TITLE
        # --------------------------------------------------

        worksheet.merge_range(
            "A1:D2",
            "CALL QUALITY EVALUATION & FEEDBACK REPORT",
            title_format
        )

        worksheet.set_row(
            0,
            25
        )

        worksheet.set_row(
            1,
            25
        )

        worksheet.merge_range(
            "A3:D3",
            "Sparta Telecom Quality Assurance",
            subtitle_format
        )

        # --------------------------------------------------
        # HEADER INFORMATION
        # --------------------------------------------------

        header_rows = [
            [
                "Agent Name:",
                report_values["Agent Name"],
                "Sale Date",
                report_values["Sale Date"]
            ],
            [
                "Campaign / Line:",
                report_values["Campaign / Line"],
                "Evaluator Name:",
                report_values["Evaluator Name"]
            ],
            [
                "Customer Name",
                report_values["Customer Name"],
                "Call Disposition:",
                report_values["Call Disposition"]
            ],
            [
                "CLI",
                report_values["CLI"],
                "Next Review Date:",
                report_values["Next Review Date"]
            ]
        ]

        start_row = 4

        for row_offset, row_values in enumerate(
            header_rows
        ):

            row_number = start_row + row_offset

            worksheet.write(
                row_number,
                0,
                row_values[0],
                label_format
            )

            worksheet.write(
                row_number,
                1,
                row_values[1],
                value_format
            )

            worksheet.write(
                row_number,
                2,
                row_values[2],
                label_format
            )

            worksheet.write(
                row_number,
                3,
                row_values[3],
                value_format
            )

            worksheet.set_row(
                row_number,
                30
            )

        # --------------------------------------------------
        # SECTION 1
        # --------------------------------------------------

        section_row = 9

        worksheet.merge_range(
            f"A{section_row + 1}:D{section_row + 1}",
            "1. Call Summary & Context",
            section_format
        )

        worksheet.merge_range(
            f"A{section_row + 2}:D{section_row + 5}",
            call_summary or "No call summary provided.",
            body_format
        )

        # --------------------------------------------------
        # SECTION 2
        # --------------------------------------------------

        section_row = 15

        worksheet.merge_range(
            f"A{section_row + 1}:D{section_row + 1}",
            "2. Key Highlights: What Went Well vs. Areas Needing Improvement",
            section_format
        )

        worksheet.write(
            section_row + 1,
            0,
            "GOODS (Strengths & Best Practices)",
            goods_header_format
        )

        worksheet.merge_range(
            section_row + 1,
            0,
            section_row + 1,
            1,
            "GOODS (Strengths & Best Practices)",
            goods_header_format
        )

        worksheet.merge_range(
            section_row + 1,
            2,
            section_row + 1,
            3,
            "BADS (Errors & Areas to Improve)",
            bads_header_format
        )

        worksheet.merge_range(
            section_row + 2,
            0,
            section_row + 6,
            1,
            goods or "No strengths recorded.",
            body_format
        )

        worksheet.merge_range(
            section_row + 2,
            2,
            section_row + 6,
            3,
            bads or "No improvement areas recorded.",
            body_format
        )

        # --------------------------------------------------
        # SECTION 3
        # --------------------------------------------------

        section_row = 24

        worksheet.merge_range(
            f"A{section_row + 1}:D{section_row + 1}",
            "3. Actionable Coaching: Do's & Don'ts Playbook",
            section_format
        )

        worksheet.merge_range(
            section_row + 1,
            0,
            section_row + 1,
            1,
            "DO'S (Recommended Scripts & Behaviours)",
            dos_header_format
        )

        worksheet.merge_range(
            section_row + 1,
            2,
            section_row + 1,
            3,
            "DON'TS (Strictly Avoid)",
            donts_header_format
        )

        worksheet.merge_range(
            section_row + 2,
            0,
            section_row + 7,
            1,
            dos or "No recommended behaviours recorded.",
            body_format
        )

        worksheet.merge_range(
            section_row + 2,
            2,
            section_row + 7,
            3,
            donts or "No prohibited behaviours recorded.",
            body_format
        )

        # --------------------------------------------------
        # ACTIONABLE COACHING
        # --------------------------------------------------

        section_row = 33

        worksheet.merge_range(
            f"A{section_row + 1}:D{section_row + 1}",
            "4. Actionable Coaching Summary",
            section_format
        )

        worksheet.merge_range(
            f"A{section_row + 2}:D{section_row + 6}",
            coaching or "No additional coaching recorded.",
            body_format
        )

        # --------------------------------------------------
        # QA RESULT SUMMARY
        # --------------------------------------------------

        section_row = 40

        worksheet.merge_range(
            f"A{section_row + 1}:D{section_row + 1}",
            "5. QA Outcome",
            section_format
        )

        worksheet.merge_range(
            f"A{section_row + 2}:B{section_row + 2}",
            "Final QA Result",
            label_format
        )

        worksheet.merge_range(
            f"C{section_row + 2}:D{section_row + 2}",
            safe_value(
                sale,
                "Final_QA_Result"
            ),
            value_format
        )

        worksheet.merge_range(
            f"A{section_row + 3}:B{section_row + 3}",
            "Quality Score",
            label_format
        )

        score_value = sale.get(
            "QA_Score",
            ""
        )

        if pd.isna(
            score_value
        ):

            score_display = ""

        else:

            try:

                score_display = (
                    f"{float(score_value):.2f}%"
                )

            except Exception:

                score_display = str(
                    score_value
                )

        worksheet.merge_range(
            f"C{section_row + 3}:D{section_row + 3}",
            score_display,
            value_format
        )

        worksheet.merge_range(
            f"A{section_row + 5}:D{section_row + 5}",
            "Generated from Sparta Telecom QA Checker",
            small_note_format
        )

        # --------------------------------------------------
        # Print area
        # --------------------------------------------------

        worksheet.print_area(
            "A1:D46"
        )

    output.seek(0)

    return output


# ==========================================================
# PDF HELPERS
# ==========================================================

def pdf_safe_text(value):

    if value is None:
        return ""

    text = str(value)

    if not text.strip():
        return ""

    # Avoid unsupported typographic characters where possible.
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u00a0": " ",
        "\u2022": "-",
    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )

    return escape(
        text
    ).replace(
        "\n",
        "<br/>"
    )


def make_pdf_styles():

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "QAReportTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor(
            "#FFFFFF"
        ),
        alignment=TA_CENTER,
        spaceAfter=0
    )

    subtitle_style = ParagraphStyle(
        "QAReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor(
            "#404040"
        ),
        alignment=TA_CENTER,
        spaceAfter=8
    )

    section_style = ParagraphStyle(
        "QAReportSection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor(
            "#FFFFFF"
        ),
        spaceBefore=7,
        spaceAfter=0
    )

    label_style = ParagraphStyle(
        "QAReportLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor(
            "#17365D"
        )
    )

    value_style = ParagraphStyle(
        "QAReportValue",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor(
            "#404040"
        )
    )

    body_style = ParagraphStyle(
        "QAReportBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor(
            "#404040"
        ),
        spaceAfter=0
    )

    small_style = ParagraphStyle(
        "QAReportSmall",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor(
            "#666666"
        ),
        alignment=TA_CENTER
    )

    column_header_style = ParagraphStyle(
        "QAReportColumnHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor(
            "#17365D"
        )
    )

    return {
        "title": title_style,
        "subtitle": subtitle_style,
        "section": section_style,
        "label": label_style,
        "value": value_style,
        "body": body_style,
        "small": small_style,
        "column_header": column_header_style
    }


def pdf_section_header(
    text,
    styles
):

    table = Table(
        [[
            Paragraph(
                pdf_safe_text(text),
                styles["section"]
            )
        ]],
        colWidths=[
            174 * mm
        ]
    )

    table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, -1),
                colors.HexColor(
                    "#2F75B5"
                )
            ),
            (
                "BOX",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor(
                    "#2F75B5"
                )
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                7
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                7
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                5
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                5
            )
        ])
    )

    return table


def create_individual_pdf(
    sale,
    answers
):
    """
    Creates the individual Call Quality Evaluation PDF.
    """

    output = BytesIO()

    base_name = sale_report_filename(
        sale
    )

    styles = make_pdf_styles()

    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm
    )

    story = []

    # ------------------------------------------------------
    # Title
    # ------------------------------------------------------

    title_table = Table(
        [[
            Paragraph(
                "CALL QUALITY EVALUATION & FEEDBACK REPORT",
                styles["title"]
            )
        ]],
        colWidths=[
            174 * mm
        ],
        rowHeights=[
            14 * mm
        ]
    )

    title_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, -1),
                colors.HexColor(
                    "#17365D"
                )
            ),
            (
                "BOX",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor(
                    "#17365D"
                )
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),
            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER"
            )
        ])
    )

    story.append(
        title_table
    )

    story.append(
        Paragraph(
            "Sparta Telecom Quality Assurance",
            styles["subtitle"]
        )
    )

    # ------------------------------------------------------
    # Header information
    # ------------------------------------------------------

    metadata = [
        [
            Paragraph(
                "Agent Name:",
                styles["label"]
            ),
            Paragraph(
                pdf_safe_text(
                    safe_value(
                        sale,
                        "Agent"
                    )
                ),
                styles["value"]
            ),
            Paragraph(
                "Sale Date:",
                styles["label"]
            ),
            Paragraph(
                pdf_safe_text(
                    safe_value(
                        sale,
                        "Sale_Date"
                    )
                ),
                styles["value"]
            )
        ],
        [
            Paragraph(
                "Campaign / Line:",
                styles["label"]
            ),
            Paragraph(
                pdf_safe_text(
                    safe_value(
                        sale,
                        "Campaign_Line"
                    )
                ),
                styles["value"]
            ),
            Paragraph(
                "Evaluator Name:",
                styles["label"]
            ),
            Paragraph(
                pdf_safe_text(
                    safe_value(
                        sale,
                        "Evaluator_Name"
                    )
                ),
                styles["value"]
            )
        ],
        [
            Paragraph(
                "Customer Name:",
                styles["label"]
            ),
            Paragraph(
                pdf_safe_text(
                    safe_value(
                        sale,
                        "Customer_Name"
                    )
                ),
                styles["value"]
            ),
            Paragraph(
                "Call Disposition:",
                styles["label"]
            ),
            Paragraph(
                pdf_safe_text(
                    safe_value(
                        sale,
                        "Call_Disposition"
                    )
                ),
                styles["value"]
            )
        ],
        [
            Paragraph(
                "CLI:",
                styles["label"]
            ),
            Paragraph(
                pdf_safe_text(
                    safe_value(
                        sale,
                        "Phone"
                    )
                ),
                styles["value"]
            ),
            Paragraph(
                "Next Review Date:",
                styles["label"]
            ),
            Paragraph(
                pdf_safe_text(
                    safe_value(
                        sale,
                        "Next_Review_Date"
                    )
                ),
                styles["value"]
            )
        ]
    ]

    metadata_table = Table(
        metadata,
        colWidths=[
            31 * mm,
            56 * mm,
            34 * mm,
            53 * mm
        ],
        repeatRows=0
    )

    metadata_table.setStyle(
        TableStyle([
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor(
                    "#D9E1F2"
                )
            ),
            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                colors.HexColor(
                    "#D9EAF7"
                )
            ),
            (
                "BACKGROUND",
                (2, 0),
                (2, -1),
                colors.HexColor(
                    "#D9EAF7"
                )
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                5
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                5
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                5
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                5
            )
        ])
    )

    story.append(
        metadata_table
    )

    story.append(
        Spacer(
            1,
            5 * mm
        )
    )

    # ------------------------------------------------------
    # Section 1
    # ------------------------------------------------------

    story.append(
        pdf_section_header(
            "1. Call Summary & Context",
            styles
        )
    )

    summary_table = Table(
        [[
            Paragraph(
                pdf_safe_text(
                    safe_value(
                        sale,
                        "Call_Summary"
                    )
                    or "No call summary provided."
                ),
                styles["body"]
            )
        ]],
        colWidths=[
            174 * mm
        ]
    )

    summary_table.setStyle(
        TableStyle([
            (
                "BOX",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor(
                    "#D9E1F2"
                )
            ),
            (
                "BACKGROUND",
                (0, 0),
                (-1, -1),
                colors.white
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                7
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                7
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                7
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                7
            )
        ])
    )

    story.append(
        summary_table
    )

    story.append(
        Spacer(
            1,
            5 * mm
        )
    )

    # ------------------------------------------------------
    # Section 2
    # ------------------------------------------------------

    story.append(
        pdf_section_header(
            "2. Key Highlights: What Went Well vs. Areas Needing Improvement",
            styles
        )
    )

    goods_header = Table(
        [[
            Paragraph(
                "GOODS (Strengths & Best Practices)",
                styles["column_header"]
            ),
            Paragraph(
                "BADS (Errors & Areas to Improve)",
                styles["column_header"]
            )
        ]],
        colWidths=[
            87 * mm,
            87 * mm
        ]
    )

    goods_header.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (0, 0),
                colors.HexColor(
                    "#E2F0D9"
                )
            ),
            (
                "BACKGROUND",
                (1, 0),
                (1, 0),
                colors.HexColor(
                    "#FCE4D6"
                )
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor(
                    "#D9E1F2"
                )
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                6
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                6
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                5
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                5
            )
        ])
    )

    story.append(
        goods_header
    )

    goods_bads = Table(
        [[
            Paragraph(
                pdf_safe_text(
                    safe_value(
                        sale,
                        "Goods"
                    )
                    or "No strengths recorded."
                ),
                styles["body"]
            ),
            Paragraph(
                pdf_safe_text(
                    safe_value(
                        sale,
                        "Bads"
                    )
                    or "No improvement areas recorded."
                ),
                styles["body"]
            )
        ]],
        colWidths=[
            87 * mm,
            87 * mm
        ]
    )

    goods_bads.setStyle(
        TableStyle([
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor(
                    "#D9E1F2"
                )
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                7
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                7
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                7
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                7
            )
        ])
    )

    story.append(
        goods_bads
    )

    story.append(
        Spacer(
            1,
            5 * mm
        )
    )

    # ------------------------------------------------------
    # Section 3
    # ------------------------------------------------------

    story.append(
        pdf_section_header(
            "3. Actionable Coaching: Do's & Don'ts Playbook",
            styles
        )
    )

    dos_donts_header = Table(
        [[
            Paragraph(
                "DO'S (Recommended Scripts & Behaviours)",
                styles["column_header"]
            ),
            Paragraph(
                "DON'TS (Strictly Avoid)",
                styles["column_header"]
            )
        ]],
        colWidths=[
            87 * mm,
            87 * mm
        ]
    )

    dos_donts_header.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (0, 0),
                colors.HexColor(
                    "#E2F0D9"
                )
            ),
            (
                "BACKGROUND",
                (1, 0),
                (1, 0),
                colors.HexColor(
                    "#FCE4D6"
                )
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor(
                    "#D9E1F2"
                )
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                6
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                6
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                5
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                5
            )
        ])
    )

    story.append(
        dos_donts_header
    )

    dos_donts = Table(
        [[
            Paragraph(
                pdf_safe_text(
                    safe_value(
                        sale,
                        "Dos"
                    )
                    or "No recommended behaviours recorded."
                ),
                styles["body"]
            ),
            Paragraph(
                pdf_safe_text(
                    safe_value(
                        sale,
                        "Donts"
                    )
                    or "No prohibited behaviours recorded."
                ),
                styles["body"]
            )
        ]],
        colWidths=[
            87 * mm,
            87 * mm
        ]
    )

    dos_donts.setStyle(
        TableStyle([
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor(
                    "#D9E1F2"
                )
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                7
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                7
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                7
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                7
            )
        ])
    )

    story.append(
        dos_donts
    )

    story.append(
        Spacer(
            1,
            5 * mm
        )
    )

    # ------------------------------------------------------
    # Section 4 - Coaching
    # ------------------------------------------------------

    story.append(
        pdf_section_header(
            "4. Actionable Coaching Summary",
            styles
        )
    )

    coaching_table = Table(
        [[
            Paragraph(
                pdf_safe_text(
                    safe_value(
                        sale,
                        "Actionable_Coaching"
                    )
                    or "No additional coaching recorded."
                ),
                styles["body"]
            )
        ]],
        colWidths=[
            174 * mm
        ]
    )

    coaching_table.setStyle(
        TableStyle([
            (
                "BOX",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor(
                    "#D9E1F2"
                )
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                7
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                7
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                7
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                7
            )
        ])
    )

    story.append(
        coaching_table
    )

    story.append(
        Spacer(
            1,
            5 * mm
        )
    )

    # ------------------------------------------------------
    # Section 5 - Outcome
    # ------------------------------------------------------

    story.append(
        pdf_section_header(
            "5. QA Outcome",
            styles
        )
    )

    score_value = sale.get(
        "QA_Score",
        ""
    )

    if pd.isna(
        score_value
    ):

        score_display = ""

    else:

        try:

            score_display = (
                f"{float(score_value):.2f}%"
            )

        except Exception:

            score_display = str(
                score_value
            )

    outcome = [
        [
            Paragraph(
                "Final QA Result",
                styles["label"]
            ),
            Paragraph(
                pdf_safe_text(
                    safe_value(
                        sale,
                        "Final_QA_Result"
                    )
                ),
                styles["value"]
            ),
            Paragraph(
                "Quality Score",
                styles["label"]
            ),
            Paragraph(
                pdf_safe_text(
                    score_display
                ),
                styles["value"]
            )
        ]
    ]

    outcome_table = Table(
        outcome,
        colWidths=[
            38 * mm,
            49 * mm,
            38 * mm,
            49 * mm
        ]
    )

    outcome_table.setStyle(
        TableStyle([
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor(
                    "#D9E1F2"
                )
            ),
            (
                "BACKGROUND",
                (0, 0),
                (0, 0),
                colors.HexColor(
                    "#D9EAF7"
                )
            ),
            (
                "BACKGROUND",
                (2, 0),
                (2, 0),
                colors.HexColor(
                    "#D9EAF7"
                )
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                6
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                6
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                6
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                6
            )
        ])
    )

    story.append(
        outcome_table
    )

    story.append(
        Spacer(
            1,
            7 * mm
        )
    )

    story.append(
        Paragraph(
            "Generated from Sparta Telecom QA Checker",
            styles["small"]
        )
    )

    # ------------------------------------------------------
    # Footer
    # ------------------------------------------------------

    def add_page_number(canvas, doc):

        canvas.saveState()

        canvas.setFont(
            "Helvetica",
            7
        )

        canvas.setFillColor(
            colors.HexColor(
                "#666666"
            )
        )

        canvas.drawString(
            18 * mm,
            8 * mm,
            "Confidential QA Report"
        )

        canvas.drawRightString(
            A4[0] - 18 * mm,
            8 * mm,
            f"Page {doc.page}"
        )

        canvas.restoreState()

    doc.build(
        story,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number
    )

    output.seek(0)

    return output


# ==========================================================
# LOAD DASHBOARD HISTORY
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
    # GOOGLE CONTROLS
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

                    with st.spinner(
                        "Reading QA history from Google Sheets..."
                    ):

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
                "Google Sheets is the persistent QA history."
            )

            st.caption(
                "Save and Submit do not perform full-sheet reads."
            )

    # ======================================================
    # UPLOAD
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

            if raw_df.shape[1] != (
                EXPECTED_COLUMN_COUNT
            ):

                st.error(
                    f"Unexpected file structure. "
                    f"Expected exactly "
                    f"{EXPECTED_COLUMN_COUNT} "
                    f"columns, but found "
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
    # CURRENT DATA
    # ======================================================

    df = st.session_state.get(
        "sales_data"
    )

    qa_answers = st.session_state.get(
        "qa_answers",
        {}
    )

    # ======================================================
    # WORKSPACE
    # ======================================================

    if df is not None:

        df = make_editable_dataframe(
            df
        )

        st.session_state[
            "sales_data"
        ] = df

        # ==================================================
        # METRICS
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
                df[
                    "Agent"
                ]
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

        if (
            selected_agent
            != "All"
        ):

            filtered_df = filtered_df[
                filtered_df[
                    "Agent"
                ].astype(str)
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
        # SALE SELECTOR
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
            # SELECTED SALE
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

                col1, col2, col3, col4 = (
                    st.columns(4)
                )

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
                    and notes.lower()
                    != "n/a"
                ):

                    st.caption(
                        "Additional Sale Notes"
                    )

                    st.info(
                        notes
                    )

                # ==============================================
                # EXISTING ANSWERS
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

                    answers[
                        "final_result"
                    ] = (
                        final_result
                        if final_result
                        != "Select Final Result"
                        else ""
                    )

                    answers[
                        "comments"
                    ] = comments

                    answers[
                        "evaluator_name"
                    ] = evaluator_name

                    answers[
                        "campaign_line"
                    ] = campaign_line

                    answers[
                        "call_disposition"
                    ] = call_disposition

                    answers[
                        "next_review_date"
                    ] = next_review_date

                    answers[
                        "call_summary"
                    ] = call_summary

                    answers[
                        "goods"
                    ] = goods

                    answers[
                        "bads"
                    ] = bads

                    answers[
                        "dos"
                    ] = dos

                    answers[
                        "donts"
                    ] = donts

                    answers[
                        "actionable_coaching"
                    ] = actionable_coaching

                    st.session_state[
                        "qa_answers"
                    ][
                        selected_qa_id
                    ] = answers

                    df = make_editable_dataframe(
                        df
                    )

                    mask = (
                        df[
                            "QA_ID"
                        ].astype(str)
                        == str(
                            selected_qa_id
                        )
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

                            st.success(
                                "Progress saved successfully "
                                "to Google Sheets."
                            )

                        except Exception as e:

                            st.warning(
                                "Progress was saved in the app, "
                                "but Google Sheet saving failed."
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

                                google_saved = True

                            except Exception as e:

                                st.warning(
                                    "QA was completed in the app, "
                                    "but the Google Sheet save failed."
                                )

                                st.exception(e)

                            # ==================================
                            # Local dashboard update
                            # ==================================

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
                                    .astype(object)
                                )

                                existing_mask = (
                                    dashboard_df_existing[
                                        "QA_ID"
                                    ].astype(str)
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

                                    matching_indices = (
                                        dashboard_df_existing.index[
                                            existing_mask
                                        ]
                                    )

                                    for index in matching_indices:

                                        for column in dashboard_df_existing.columns:

                                            if (
                                                column
                                                not in updated_sale.index
                                            ):

                                                continue

                                            value = (
                                                updated_sale[
                                                    column
                                                ]
                                            )

                                            if pd.isna(
                                                value
                                            ):

                                                value = ""

                                            dashboard_df_existing.at[
                                                index,
                                                column
                                            ] = value

                                else:

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

                                    dashboard_df_existing = (
                                        pd.concat(
                                            [
                                                dashboard_df_existing,
                                                pd.DataFrame([
                                                    new_row_data
                                                ]).astype(object)
                                            ],
                                            ignore_index=True
                                        )
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

                            # ==================================
                            # Result display
                            # ==================================

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
                # INDIVIDUAL REPORT DOWNLOADS
                # ==============================================

                st.divider()

                st.subheader(
                    "📄 Download Individual QA Report"
                )

                # --------------------------------------------------
                # IMPORTANT:
                # Build the latest sale data from the dataframe,
                # so the download reflects what was just entered.
                # --------------------------------------------------

                latest_sale_rows = df[
                    df[
                        "QA_ID"
                    ].astype(str)
                    == str(selected_qa_id)
                ]

                if not latest_sale_rows.empty:

                    latest_sale = (
                        latest_sale_rows.iloc[0]
                    )

                    latest_answers = (
                        st.session_state[
                            "qa_answers"
                        ].get(
                            selected_qa_id,
                            {}
                        )
                    )

                    report_base_name = (
                        sale_report_filename(
                            latest_sale
                        )
                    )

                    # ------------------------------------------------
                    # Generate files
                    # ------------------------------------------------

                    try:

                        individual_excel = (
                            create_individual_excel(
                                latest_sale,
                                latest_answers
                            )
                        )

                        individual_pdf = (
                            create_individual_pdf(
                                latest_sale,
                                latest_answers
                            )
                        )

                        col1, col2 = st.columns(2)

                        with col1:

                            st.download_button(
                                "⬇️ Download Excel Report",
                                data=individual_excel.getvalue(),
                                file_name=(
                                    report_base_name
                                    + ".xlsx"
                                ),
                                mime=(
                                    "application/vnd.openxmlformats-officedocument."
                                    "spreadsheetml.sheet"
                                ),
                                use_container_width=True,
                                key=(
                                    f"download_excel_"
                                    f"{selected_qa_id}"
                                )
                            )

                        with col2:

                            st.download_button(
                                "⬇️ Download PDF Report",
                                data=individual_pdf.getvalue(),
                                file_name=(
                                    report_base_name
                                    + ".pdf"
                                ),
                                mime="application/pdf",
                                use_container_width=True,
                                key=(
                                    f"download_pdf_"
                                    f"{selected_qa_id}"
                                )
                            )

                    except Exception as e:

                        st.error(
                            "Could not generate the individual "
                            "QA report files."
                        )

                        st.exception(e)

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
                # ALL-RECORD EXCEL EXPORT
                # ==============================================

                st.divider()

                st.subheader(
                    "Export All QA Data"
                )

                # Reuse the existing two-sheet export
                # functionality.

                all_excel = BytesIO()

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

                detailed_rows = []

                for _, row in df.iterrows():

                    qa_id = row[
                        "QA_ID"
                    ]

                    row_answers = (
                        st.session_state[
                            "qa_answers"
                        ].get(
                            qa_id,
                            {}
                        )
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
                        ] = row_answers.get(
                            parameter_id,
                            "Yes"
                        )

                    detailed_rows.append(
                        detailed_row
                    )

                detailed_df = pd.DataFrame(
                    detailed_rows
                )

                with pd.ExcelWriter(
                    all_excel,
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

                all_excel.seek(0)

                st.download_button(
                    "⬇️ Download All QA Data",
                    data=all_excel.getvalue(),
                    file_name="Sparta_QA_Results.xlsx",
                    mime=(
                        "application/vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    ),
                    use_container_width=True,
                    key="download_all_qa"
                )

    else:

        st.info(
            "Upload a daily sales Excel file above "
            "or use Google Sheet Sync to load existing QA records."
        )


# ################################################################
# AGENT DASHBOARD
# ################################################################

with dashboard_tab:

    st.subheader(
        "📊 Agent Performance Dashboard"
    )

    st.caption(
        "Historical QA performance from the persistent Google Sheet."
    )

    # ======================================================
    # AUTOLOAD
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
            "Refresh reads the QA Records and QA Answers sheets once."
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
    # DASHBOARD DATA
    # ======================================================

    dashboard_df = st.session_state.get(
        "dashboard_df"
    )

    dashboard_answers = st.session_state.get(
        "dashboard_answers",
        {}
    )

    if dashboard_df is None:

        st.info(
            "No historical QA records are currently available."
        )

    elif dashboard_df.empty:

        st.info(
            "Google Sheets does not contain any QA records yet."
        )

    else:

        dashboard_df = (
            dashboard_df
            .copy()
            .astype(object)
        )

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

            if not dashboard_filtered.empty:

                # ==========================================
                # AGENT FILTER
                # ==========================================

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
                # KPI
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
                # OUTCOME
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
                    "Yes % = Yes responses ÷ applicable checks. "
                    "N/A is excluded."
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
