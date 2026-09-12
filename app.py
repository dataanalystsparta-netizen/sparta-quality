import streamlit as st
import pandas as pd
import gspread
import hashlib

from io import BytesIO
from datetime import datetime, date
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
# GOOGLE SHEET
# ==========================================================

GOOGLE_SHEET_ID = (
    "1Rk1sxO6rcJze5TTMI-7wz8x63Mw_r8qLB63Q2TPe9H4"
)

QA_RECORDS_SHEET = "QA Records"
QA_ANSWERS_SHEET = "QA Answers"
QA_PARAMETERS_SHEET = "QA Parameters"
AGENT_SUMMARY_SHEET = "Agent Summary"


# ==========================================================
# FIXED 40-COLUMN SALES FILE
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

EXPECTED_COLUMN_COUNT = 40


# ==========================================================
# FINAL RESULT OPTIONS
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

# Add parameter numbers here later.
#
# Example:
#
# FATAL_PARAMETERS = {23, 27}

FATAL_PARAMETERS = set()


# ==========================================================
# SAFE VALUE
# ==========================================================

def safe_value(row, column_name):

    if column_name not in row.index:
        return ""

    value = row[column_name]

    if pd.isna(value):
        return ""

    return str(value).strip()


# ==========================================================
# CURRENT TIMESTAMP
# ==========================================================

def current_timestamp():

    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
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
# MAKE EDITABLE DATAFRAME
# ==========================================================

def make_editable_dataframe(df):

    df = df.copy()

    editable_columns = [
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

    for column in editable_columns:

        if column in df.columns:

            df[column] = df[column].astype(object)

    return df


# ==========================================================
# PREPARE DATA
# ==========================================================

def prepare_dataframe(df):

    df = df.copy()

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

    df = make_editable_dataframe(
        df
    )

    return df


# ==========================================================
# SCORING
# ==========================================================

def calculate_score(answers):

    applicable = [
        answer
        for parameter_id, answer in answers.items()
        if isinstance(parameter_id, int)
        and answer in ["Yes", "No"]
    ]

    if not applicable:

        return 0.0

    yes_count = sum(
        1
        for answer in applicable
        if answer == "Yes"
    )

    return round(
        (
            yes_count
            / len(applicable)
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
# GOOGLE SHEETS CLIENT
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
# GOOGLE WORKSHEETS
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

    if not worksheet.get_all_values():

        worksheet.update(
            "A1",
            [headers]
        )

    return worksheet


def initialise_google_sheets():

    spreadsheet = get_spreadsheet()

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

    answer_headers = (
        ["QA_ID"]
        + [
            f"Parameter_{i}"
            for i in range(1, 29)
        ]
        + ["Last_Updated"]
    )

    answers_ws = ensure_worksheet(
        spreadsheet,
        QA_ANSWERS_SHEET,
        answer_headers
    )

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

    # Populate parameters if not already present
    parameter_values = (
        parameters_ws.get_all_values()
    )

    if len(parameter_values) <= 1:

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
                    if parameter_id
                    in FATAL_PARAMETERS
                    else "No"
                ),
                1,
                "Yes"
            ])

        parameters_ws.append_rows(
            parameter_rows,
            value_input_option="USER_ENTERED"
        )

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
# FIND GOOGLE ROW
# ==========================================================

def find_google_row(
    worksheet,
    qa_id
):

    records = (
        worksheet.get_all_records()
    )

    for index, record in enumerate(
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

            return index

    return None


# ==========================================================
# ROW → GOOGLE RECORD
# ==========================================================

def row_to_records_values(row):

    values = []

    # Original sale fields
    for column in COLUMN_NAMES:

        values.append(
            safe_value(
                row,
                column
            )
        )

    # QA/report fields
    fields = [
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

    for field in fields:

        value = (
            row[field]
            if field in row.index
            else ""
        )

        if pd.isna(value):

            value = ""

        if isinstance(
            value,
            bool
        ):

            value = (
                "TRUE"
                if value
                else "FALSE"
            )

        values.append(
            str(value)
        )

    return values


# ==========================================================
# SAVE ONE SALE TO GOOGLE
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
    # Records
    # ------------------------------------------------------

    record_values = (
        row_to_records_values(
            sale_row
        )
    )

    record_row = find_google_row(
        records_ws,
        qa_id
    )

    if record_row:

        records_ws.update(
            f"A{record_row}:"
            f"{column_letter(len(record_values))}"
            f"{record_row}",
            [record_values],
            value_input_option="USER_ENTERED"
        )

    else:

        records_ws.append_row(
            record_values,
            value_input_option="USER_ENTERED"
        )

    # ------------------------------------------------------
    # Answers
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

    answer_row = find_google_row(
        answers_ws,
        qa_id
    )

    if answer_row:

        answers_ws.update(
            f"A{answer_row}:"
            f"{column_letter(len(answer_values))}"
            f"{answer_row}",
            [answer_values],
            value_input_option="USER_ENTERED"
        )

    else:

        answers_ws.append_row(
            answer_values,
            value_input_option="USER_ENTERED"
        )


# ==========================================================
# SYNC GOOGLE SHEET → APP
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
    # QA score
    # ------------------------------------------------------

    if "QA_Score" in records_df.columns:

        records_df["QA_Score"] = (
            pd.to_numeric(
                records_df["QA_Score"],
                errors="coerce"
            )
            .astype(object)
        )

    # ------------------------------------------------------
    # Fatal
    # ------------------------------------------------------

    if "Fatal_Failure" in records_df.columns:

        records_df["Fatal_Failure"] = (
            records_df[
                "Fatal_Failure"
            ]
            .astype(str)
            .str.upper()
            .isin(
                [
                    "TRUE",
                    "YES",
                    "1"
                ]
            )
            .astype(object)
        )

    # ------------------------------------------------------
    # Answers
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

            value = record.get(
                f"Parameter_{parameter_id}",
                "Yes"
            )

            if value not in [
                "Yes",
                "No",
                "N/A"
            ]:

                value = "Yes"

            answers[
                parameter_id
            ] = value

        # Pull report/comment information from
        # QA Records too, so the session has one
        # consistent object.
        matching = records_df[
            records_df["QA_ID"].astype(str)
            == qa_id
        ]

        if not matching.empty:

            row = matching.iloc[0]

            answers["final_result"] = (
                safe_value(
                    row,
                    "Final_QA_Result"
                )
            )

            answers["comments"] = (
                safe_value(
                    row,
                    "QA_Comments"
                )
            )

            answers["evaluator_name"] = (
                safe_value(
                    row,
                    "Evaluator_Name"
                )
            )

            answers["campaign_line"] = (
                safe_value(
                    row,
                    "Campaign_Line"
                )
            )

            answers["call_disposition"] = (
                safe_value(
                    row,
                    "Call_Disposition"
                )
            )

            answers["next_review_date"] = (
                safe_value(
                    row,
                    "Next_Review_Date"
                )
            )

            answers["call_summary"] = (
                safe_value(
                    row,
                    "Call_Summary"
                )
            )

            answers["goods"] = (
                safe_value(
                    row,
                    "Goods"
                )
            )

            answers["bads"] = (
                safe_value(
                    row,
                    "Bads"
                )
            )

            answers["dos"] = (
                safe_value(
                    row,
                    "Dos"
                )
            )

            answers["donts"] = (
                safe_value(
                    row,
                    "Donts"
                )
            )

            answers[
                "actionable_coaching"
            ] = (
                safe_value(
                    row,
                    "Actionable_Coaching"
                )
            )

        qa_answers[
            qa_id
        ] = answers

    return (
        records_df,
        qa_answers
    )


# ==========================================================
# UPDATE AGENT SUMMARY SHEET
# ==========================================================

def update_agent_summary(df):

    sheets = initialise_google_sheets()

    worksheet = sheets[
        "summary"
    ]

    completed = df[
        df["QA_Status"]
        == "Completed"
    ].copy()

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

    if completed.empty:

        return

    output_rows = []

    for agent, group in completed.groupby(
        "Agent",
        dropna=False
    ):

        scores = pd.to_numeric(
            group["QA_Score"],
            errors="coerce"
        )

        average_score = (
            scores.mean()
            if scores.notna().any()
            else 0
        )

        output_rows.append([
            str(agent),
            len(group),
            round(
                average_score,
                2
            ),
            int(
                (
                    group["Final_QA_Result"]
                    == "Approved"
                ).sum()
            ),
            int(
                (
                    group["Final_QA_Result"]
                    == "Rejected"
                ).sum()
            ),
            int(
                (
                    group["Final_QA_Result"]
                    == "Cancelled"
                ).sum()
            ),
            int(
                (
                    group["Final_QA_Result"]
                    == "Reworked Required"
                ).sum()
            ),
            int(
                (
                    group["Final_QA_Result"]
                    == "Hold"
                ).sum()
            ),
            int(
                group["Fatal_Failure"].sum()
            )
        ])

    if output_rows:

        worksheet.append_rows(
            output_rows,
            value_input_option="USER_ENTERED"
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
    # Summary sheet
    # ------------------------------------------------------

    result_columns = [
        "QA_ID",
        "Sale_Date",
        "Agent",
        "Verifier",
        "Customer_Name",
        "Phone",
        "Current_Provider",
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
        "QA_Comments"
    ]

    results_df = df[
        [
            col
            for col in result_columns
            if col in df.columns
        ]
    ].copy()

    # ------------------------------------------------------
    # Detailed sheet
    # ------------------------------------------------------

    detailed_rows = []

    for _, row in df.iterrows():

        qa_id = row["QA_ID"]

        answers = qa_answers.get(
            qa_id,
            {}
        )

        detail = {
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

            detail[
                f"Parameter_{parameter_id}"
            ] = answers.get(
                parameter_id,
                "Yes"
            )

        detailed_rows.append(
            detail
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

                    width = 32

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
# PARAMETER PERFORMANCE
# ==========================================================

def parameter_performance(
    df,
    qa_answers
):

    completed = df[
        df["QA_Status"]
        == "Completed"
    ].copy()

    rows = []

    if completed.empty:

        return pd.DataFrame()

    for parameter_id in range(
        1,
        29
    ):

        question = QA_QUESTIONS[
            parameter_id - 1
        ]

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
            "Question": question,
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
# AGENT PARAMETER PERFORMANCE
# ==========================================================

def agent_parameter_performance(
    df,
    qa_answers,
    agent
):

    if agent == "All":

        return parameter_performance(
            df,
            qa_answers
        )

    agent_df = df[
        (
            df["Agent"].astype(str)
            == str(agent)
        )
        &
        (
            df["QA_Status"]
            == "Completed"
        )
    ].copy()

    if agent_df.empty:

        return pd.DataFrame()

    rows = []

    for parameter_id in range(
        1,
        29
    ):

        yes_count = 0
        no_count = 0
        na_count = 0

        for qa_id in agent_df[
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
# SESSION STATE
# ==========================================================

if "qa_answers" not in st.session_state:

    st.session_state[
        "qa_answers"
    ] = {}

if "sales_data" not in st.session_state:

    st.session_state[
        "sales_data"
    ] = None

if "uploaded_file_key" not in st.session_state:

    st.session_state[
        "uploaded_file_key"
    ] = None


# ==========================================================
# HEADER
# ==========================================================

st.title(
    "Sparta QA Checker"
)

st.caption(
    "Sales QA • Persistent Google Sheets • "
    "Agent Performance • Parameter Analysis"
)


# ==========================================================
# GOOGLE SHEET CONTROLS
# ==========================================================

with st.expander(
    "☁️ Google Sheet",
    expanded=False
):

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "🔄 Sync Google Sheet",
            use_container_width=True
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
            "Google Sheets is the persistent QA "
            "store and backup."
        )


# ==========================================================
# FILE UPLOAD
# ==========================================================

uploaded_file = st.file_uploader(
    "Upload Daily Sales Excel File",
    type=[
        "xlsx",
        "xls"
    ]
)


# ==========================================================
# PROCESS UPLOAD
# ==========================================================

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

        raw_df.columns = (
            COLUMN_NAMES
        )

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

            df = prepare_dataframe(
                raw_df
            )

            st.session_state[
                "sales_data"
            ] = df

            st.session_state[
                "qa_answers"
            ] = {}

            st.session_state[
                "uploaded_file_key"
            ] = upload_key

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

if st.session_state[
    "sales_data"
] is not None:

    df = make_editable_dataframe(
        st.session_state[
            "sales_data"
        ]
    )

    st.session_state[
        "sales_data"
    ] = df

    qa_answers = st.session_state[
        "qa_answers"
    ]

    # ======================================================
    # OVERALL DASHBOARD
    # ======================================================

    st.divider()

    st.subheader(
        "QA Dashboard"
    )

    total_sales = len(df)

    pending_count = int(
        (
            df["QA_Status"]
            == "Quality Pending"
        ).sum()
    )

    completed_count = int(
        (
            df["QA_Status"]
            == "Completed"
        ).sum()
    )

    approved_count = int(
        (
            df["Final_QA_Result"]
            == "Approved"
        ).sum()
    )

    rejected_count = int(
        (
            df["Final_QA_Result"]
            == "Rejected"
        ).sum()
    )

    col1, col2, col3, col4, col5 = st.columns(5)

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

    # ======================================================
    # FIND SALE
    # ======================================================

    st.divider()

    st.subheader(
        "Find Sale"
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        agents = [
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
            agents
        )

    filtered_df = df.copy()

    if selected_agent != "All":

        filtered_df = filtered_df[
            filtered_df["Agent"]
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
            ]
        )

    if selected_status != "All":

        filtered_df = filtered_df[
            filtered_df["QA_Status"]
            == selected_status
        ]

    with col3:

        selected_result = st.selectbox(
            "Final Result",
            [
                "All"
            ] + FINAL_RESULTS
        )

    if selected_result != "All":

        filtered_df = filtered_df[
            filtered_df[
                "Final_QA_Result"
            ]
            == selected_result
        ]

    # ======================================================
    # SELECT SALE
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

        sale_options = (
            filtered_df[
                "QA_ID"
            ]
            .tolist()
        )

        selected_qa_id = st.selectbox(
            "Sale",
            sale_options,
            format_func=lambda x: sale_label(
                df,
                x
            )
        )

        selected_rows = df[
            df["QA_ID"]
            == selected_qa_id
        ]

        sale = selected_rows.iloc[0]

        # ==================================================
        # SALE DETAILS
        # ==================================================

        st.divider()

        st.subheader(
            "Sale Details"
        )

        col1, col2, col3, col4 = st.columns(4)

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

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.caption("Sale Date")
            st.write(
                safe_value(
                    sale,
                    "Sale_Date"
                )
            )

        with col2:
            st.caption("Current Provider")
            st.write(
                safe_value(
                    sale,
                    "Current_Provider"
                )
            )

        with col3:
            st.caption("Broadband Type")
            st.write(
                safe_value(
                    sale,
                    "Broadband_Type"
                )
            )

        with col4:
            st.caption("Payment Method")
            st.write(
                safe_value(
                    sale,
                    "Payment_Method"
                )
            )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.caption("Package")
            st.write(
                safe_value(
                    sale,
                    "Package_Offered"
                )
            )

        with col2:
            st.caption("Service")
            st.write(
                safe_value(
                    sale,
                    "Service"
                )
            )

        with col3:
            st.caption("Router Charges")
            st.write(
                safe_value(
                    sale,
                    "Router_Charges"
                )
            )

        with col4:
            st.caption("Contract Duration")
            st.write(
                safe_value(
                    sale,
                    "Contract_Duration"
                )
            )

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
            qa_answers.get(
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

        st.caption(
            "All questions default to Yes. "
            "Change to No or N/A where appropriate."
        )

        with st.form(
            key=f"qa_form_{selected_qa_id}"
        ):

            answers = {}

            for parameter_id, question in enumerate(
                QA_QUESTIONS,
                start=1
            ):

                question_col, answer_col = st.columns(
                    [7.5, 2.5],
                    vertical_alignment="center"
                )

                with question_col:

                    if parameter_id in FATAL_PARAMETERS:

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
                    ] = answer

                st.write("")

            # ==================================================
            # REPORT FIELDS
            # ==================================================

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

            # ==================================================
            # FINAL RESULT
            # ==================================================

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

            if previous_final_result in FINAL_RESULTS:

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
        # COMMON ANSWER STORAGE
        # ==================================================

        if save_progress or submit_final:

            answers["final_result"] = (
                final_result
                if final_result
                != "Select Final Result"
                else ""
            )

            answers["comments"] = comments

            answers["evaluator_name"] = (
                evaluator_name
            )

            answers["campaign_line"] = (
                campaign_line
            )

            answers["call_disposition"] = (
                call_disposition
            )

            answers["next_review_date"] = (
                next_review_date
            )

            answers["call_summary"] = (
                call_summary
            )

            answers["goods"] = goods
            answers["bads"] = bads
            answers["dos"] = dos
            answers["donts"] = donts

            answers[
                "actionable_coaching"
            ] = actionable_coaching

            # Store answers
            st.session_state[
                "qa_answers"
            ][selected_qa_id] = answers

            # Re-fetch editable dataframe
            df = make_editable_dataframe(
                df
            )

            mask = (
                df["QA_ID"]
                == selected_qa_id
            )

            # Current score
            score = calculate_score(
                answers
            )

            fatal_failure = (
                has_fatal_failure(
                    answers
                )
            )

            # --------------------------------------------------
            # Save Progress
            # --------------------------------------------------

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

                # Remain pending
                df.loc[
                    mask,
                    "QA_Status"
                ] = "Quality Pending"

                report_values = {
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

                for column, value in report_values.items():

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
                        "Progress was saved in the "
                        "current app session, but "
                        "Google Sheet synchronization failed."
                    )

                    st.exception(e)

            # --------------------------------------------------
            # Final Submit
            # --------------------------------------------------

            if submit_final:

                if final_result == "Select Final Result":

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

                    report_values = {
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

                    for column, value in report_values.items():

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

                    if google_saved:

                        st.success(
                            "✓ QA result backed up to Google Sheets."
                        )

    # ======================================================
    # AGENT QUALITY DASHBOARD
    # ======================================================

    st.divider()

    st.subheader(
        "📊 Agent Quality Dashboard"
    )

    completed = df[
        df["QA_Status"]
        == "Completed"
    ].copy()

    if completed.empty:

        st.info(
            "Complete QA records to populate "
            "the agent performance dashboard."
        )

    else:

        # --------------------------------------------------
        # Date range
        # --------------------------------------------------

        parsed_dates = pd.to_datetime(
            completed["Sale_Date"],
            errors="coerce",
            dayfirst=True
        )

        valid_dates = parsed_dates.dropna()

        if valid_dates.empty:

            st.warning(
                "Sale dates could not be interpreted "
                "for dashboard filtering."
            )

            dashboard_df = completed.copy()

        else:

            min_date = valid_dates.min().date()
            max_date = valid_dates.max().date()

            col1, col2 = st.columns(2)

            with col1:

                start_date = st.date_input(
                    "From",
                    value=min_date,
                    min_value=min_date,
                    max_value=max_date
                )

            with col2:

                end_date = st.date_input(
                    "To",
                    value=max_date,
                    min_value=min_date,
                    max_value=max_date
                )

            if start_date > end_date:

                st.error(
                    "The start date cannot be after "
                    "the end date."
                )

                dashboard_df = completed.iloc[0:0].copy()

            else:

                date_mask = (
                    (
                        pd.to_datetime(
                            completed["Sale_Date"],
                            errors="coerce",
                            dayfirst=True
                        ).dt.date
                        >= start_date
                    )
                    &
                    (
                        pd.to_datetime(
                            completed["Sale_Date"],
                            errors="coerce",
                            dayfirst=True
                        ).dt.date
                        <= end_date
                    )
                )

                dashboard_df = completed[
                    date_mask
                ].copy()

        # --------------------------------------------------
        # Agent filter for dashboard
        # --------------------------------------------------

        dashboard_agents = [
            "All"
        ] + sorted(
            dashboard_df["Agent"]
            .fillna("")
            .astype(str)
            .unique()
            .tolist()
        )

        dashboard_agent = st.selectbox(
            "Dashboard Agent",
            dashboard_agents
        )

        if dashboard_agent != "All":

            dashboard_df = dashboard_df[
                dashboard_df["Agent"]
                .astype(str)
                == dashboard_agent
            ]

        # --------------------------------------------------
        # KPI metrics
        # --------------------------------------------------

        if dashboard_df.empty:

            st.info(
                "No completed QA records match "
                "the selected dashboard filters."
            )

        else:

            dashboard_scores = pd.to_numeric(
                dashboard_df["QA_Score"],
                errors="coerce"
            )

            avg_score = (
                dashboard_scores.mean()
                if dashboard_scores.notna().any()
                else 0
            )

            fatal_count = int(
                dashboard_df[
                    "Fatal_Failure"
                ]
                .fillna(False)
                .astype(bool)
                .sum()
            )

            rework_count = int(
                (
                    dashboard_df[
                        "Final_QA_Result"
                    ]
                    == "Reworked Required"
                ).sum()
            )

            hold_count = int(
                (
                    dashboard_df[
                        "Final_QA_Result"
                    ]
                    == "Hold"
                ).sum()
            )

            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:

                st.metric(
                    "Sales Checked",
                    len(dashboard_df)
                )

            with col2:

                st.metric(
                    "Average QA Score",
                    f"{avg_score:.2f}%"
                )

            with col3:

                st.metric(
                    "Reworked",
                    rework_count
                )

            with col4:

                st.metric(
                    "Hold",
                    hold_count
                )

            with col5:

                st.metric(
                    "Fatal Failures",
                    fatal_count
                )

            # --------------------------------------------------
            # Agent ranking table
            # --------------------------------------------------

            st.markdown(
                "### Agent Performance"
            )

            agent_rows = []

            for agent, group in dashboard_df.groupby(
                "Agent",
                dropna=False
            ):

                agent_scores = pd.to_numeric(
                    group["QA_Score"],
                    errors="coerce"
                )

                average = (
                    agent_scores.mean()
                    if agent_scores.notna().any()
                    else 0
                )

                sales_checked = len(
                    group
                )

                approved = int(
                    (
                        group["Final_QA_Result"]
                        == "Approved"
                    ).sum()
                )

                rejected = int(
                    (
                        group["Final_QA_Result"]
                        == "Rejected"
                    ).sum()
                )

                cancelled = int(
                    (
                        group["Final_QA_Result"]
                        == "Cancelled"
                    ).sum()
                )

                reworked = int(
                    (
                        group["Final_QA_Result"]
                        == "Reworked Required"
                    ).sum()
                )

                hold = int(
                    (
                        group["Final_QA_Result"]
                        == "Hold"
                    ).sum()
                )

                fatal = int(
                    group["Fatal_Failure"]
                    .fillna(False)
                    .astype(bool)
                    .sum()
                )

                agent_rows.append({
                    "Agent": str(agent),
                    "Sales Checked": sales_checked,
                    "Average QA Score": round(
                        average,
                        2
                    ),
                    "Approved": approved,
                    "Rejected": rejected,
                    "Cancelled": cancelled,
                    "Reworked": reworked,
                    "Hold": hold,
                    "Fatal Failures": fatal
                })

            agent_table = pd.DataFrame(
                agent_rows
            )

            agent_table = agent_table.sort_values(
                "Average QA Score",
                ascending=False
            )

            st.dataframe(
                agent_table,
                use_container_width=True,
                hide_index=True
            )

            # ==================================================
            # PARAMETER PERFORMANCE
            # ==================================================

            st.divider()

            st.markdown(
                "### Parameter Performance"
            )

            st.caption(
                "This shows the percentage of applicable "
                "QA checks receiving Yes for each parameter."
            )

            parameter_df = parameter_performance(
                dashboard_df,
                qa_answers
            )

            if not parameter_df.empty:

                display_parameter_df = (
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
                        "Yes %",
                        ascending=True
                    )
                    .reset_index(drop=True)
                )

                st.dataframe(
                    display_parameter_df,
                    use_container_width=True,
                    hide_index=True
                )

                # --------------------------------------------------
                # Weakest parameters
                # --------------------------------------------------

                st.markdown(
                    "### Areas Needing Most Attention"
                )

                weakest = parameter_df[
                    parameter_df[
                        "Applicable"
                    ] > 0
                ].sort_values(
                    "Yes %"
                ).head(5)

                if not weakest.empty:

                    for _, item in weakest.iterrows():

                        st.write(
                            f"**Parameter "
                            f"{int(item['Parameter'])} — "
                            f"{item['Yes %']:.2f}% Yes**  \n"
                            f"{item['Question']}"
                        )

                # ==================================================
                # AGENT-SPECIFIC PARAMETER BREAKDOWN
                # ==================================================

                st.divider()

                st.markdown(
                    "### Agent Parameter Breakdown"
                )

                agent_breakdown_options = [
                    "All"
                ] + sorted(
                    dashboard_df["Agent"]
                    .fillna("")
                    .astype(str)
                    .unique()
                    .tolist()
                )

                breakdown_agent = st.selectbox(
                    "Select Agent",
                    agent_breakdown_options,
                    key="parameter_agent_breakdown"
                )

                agent_parameter_df = (
                    agent_parameter_performance(
                        dashboard_df,
                        qa_answers,
                        breakdown_agent
                    )
                )

                if not agent_parameter_df.empty:

                    st.dataframe(
                        agent_parameter_df[
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

    # ======================================================
    # CURRENT QA RESULTS
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
    # EXPORT
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
