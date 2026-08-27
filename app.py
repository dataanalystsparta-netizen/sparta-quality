import streamlit as st
import pandas as pd
import os
from datetime import datetime, date
from fpdf import FPDF
import io

# ==========================================
# CONFIGURATION & DATA STRUCTURES
# ==========================================

# Path to your local network Excel file (2-way database)
# Change this to your actual shared drive path, e.g., "\\\\Server\\Shared\\QA_Database.xlsx"
DB_FILE_PATH = "qa_database.xlsx"

# Define the 28 QA Questions. Set "fatal": True for auto-fail parameters.
QA_CHECKLIST = [
    {"id": 1, "text": "Did the agent greet the customer and introduce themselves and the company properly?", "fatal": False},
    {"id": 2, "text": "Did the agent clearly inform the purpose of the call in a professional and customer-centric manner?", "fatal": False},
    {"id": 3, "text": "Did the agent avoid inappropriate opening remarks (e.g., referring to the customer as 'retired or pensioner')?", "fatal": True},
    {"id": 4, "text": "Did the agent confirm the customer’s current service provider and type of line (e.g., copper/fiber)?", "fatal": False},
    {"id": 5, "text": "Did the agent ask about the customer’s current usage or bill amount to tailor their offer?", "fatal": False},
    {"id": 6, "text": "Did the agent confirm if the customer is under contract with their current provider?", "fatal": False},
    {"id": 7, "text": "Did the agent ask about any additional services (extension lines, cordless phones, TV, BB & Type of BB)?", "fatal": False},
    {"id": 8, "text": "Did the agent appropriately compare Sparta Telecom's offerings with the customer’s current provider?", "fatal": False},
    {"id": 9, "text": "Did the agent verify the customer’s awareness of their current service details (bills, provider name)?", "fatal": False},
    {"id": 10, "text": "Did the agent confirm today's date or check for signs of vulnerability (e.g., customer being unclear/confused)?", "fatal": True},
    {"id": 11, "text": "Did the agent effectively engage the customer by asking personalized questions (rapport building)?", "fatal": False},
    {"id": 12, "text": "Did the agent explain savings AND quick support services in a way that aligned with the customer's situation?", "fatal": False},
    {"id": 13, "text": "Did the agent offer an appropriate package based on the customer’s usage and preferences?", "fatal": False},
    {"id": 14, "text": "Did the agent explain VAT, call setup fees, and any other charges clearly?", "fatal": True},
    {"id": 15, "text": "Did the agent mention the 24-month price guarantee or any other relevant contract terms?", "fatal": False},
    {"id": 16, "text": "Did the agent clarify that Sparta Telecom is a separate company to avoid confusion?", "fatal": False},
    {"id": 17, "text": "Did the agent collect all necessary details (Name, DOB, address, email, alternate contact) accurately?", "fatal": False},
    {"id": 18, "text": "Did the agent confirm the customer’s payment mode and attempt to collect direct debit details professionally?", "fatal": False},
    {"id": 19, "text": "Did the agent verify the decision-maker or presence of family interference (if applicable)?", "fatal": True},
    {"id": 20, "text": "Did the agent refrain from mentioning the cooling-off period and customer rights without being asked?", "fatal": False},
    {"id": 21, "text": "Did the agent disclose router charges, line import charges, or broadband downgrade/removal charges if applicable?", "fatal": True},
    {"id": 22, "text": "Did the agent explain any health alarm systems, itemized billing, or calling features if relevant?", "fatal": False},
    {"id": 23, "text": "Did the agent avoid pressuring, compelling, or misleading the customer into agreeing to the sale?", "fatal": True},
    {"id": 24, "text": "Did the agent confirm that the customer is happy and satisfied with the package being offered?", "fatal": False},
    {"id": 25, "text": "Did the agent ensure there was no confusion about proceeding with the package/sale?", "fatal": False},
    {"id": 26, "text": "Did the verifier perform the script verbatim and follow compliance guidelines?", "fatal": True},
    {"id": 27, "text": "Did the verifier ensure all customer details and payment details were accurate and matched the recorded sale?", "fatal": False},
    {"id": 28, "text": "Did the verifier confirm that the sale was properly explained and not based solely on paperwork?", "fatal": False},
]

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def load_database():
    """Loads the Excel database. Creates it if it doesn't exist."""
    if os.path.exists(DB_FILE_PATH):
        try:
            df = pd.read_excel(DB_FILE_PATH)
            return df
        except Exception as e:
            st.error(f"Error reading database: {e}. Ensure the file isn't open in Excel.")
            return pd.DataFrame()
    return pd.DataFrame()

def save_to_database(new_record):
    """Appends a new record to the Excel database."""
    df = load_database()
    new_df = pd.DataFrame([new_record])
    
    if df.empty:
        combined_df = new_df
    else:
        combined_df = pd.concat([df, new_df], ignore_index=True)
        
    try:
        combined_df.to_excel(DB_FILE_PATH, index=False)
        return True
    except Exception as e:
        st.error(f"Error saving to database: {e}. Ensure the file isn't open in Excel by another user.")
        return False

def calculate_score(responses):
    """Calculates the QA score and checks for fatal errors."""
    total_questions = len(QA_CHECKLIST)
    yes_count = 0
    fatal_failed = False
    fatal_questions_failed = []

    for q in QA_CHECKLIST:
        q_id = str(q['id'])
        if responses.get(q_id) == "Yes":
            yes_count += 1
        elif responses.get(q_id) == "No" and q['fatal']:
            fatal_failed = True
            fatal_questions_failed.append(q['id'])

    score = (yes_count / total_questions) * 100
    
    if fatal_failed:
        score = 0.0 # Auto-fail sets score to 0
        
    return round(score, 2), fatal_failed, fatal_questions_failed

def generate_pdf(report_data):
    """Generates a PDF report for a specific QA evaluation."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Sparta Telecom - QA Evaluation Report", 0, 1, 'C')
    pdf.ln(5)
    
    # Metadata
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"Call Reference: {report_data['call_id']}", 0, 1)
    pdf.cell(0, 8, f"Agent Name: {report_data['agent_name']}", 0, 1)
    pdf.cell(0, 8, f"Date of Call: {report_data['call_date']}", 0, 1)
    pdf.cell(0, 8, f"Evaluator: {report_data['evaluator_name']}", 0, 1)
    pdf.ln(5)
    
    # Score
    pdf.set_font("Arial", 'B', 14)
    status = "AUTO-FAIL (Fatal Error)" if report_data['fatal_fail'] else "PASS"
    color = (255, 0, 0) if report_data['fatal_fail'] else (0, 128, 0)
    pdf.set_text_color(*color)
    pdf.cell(0, 10, f"Final Score: {report_data['score']}% - {status}", 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    # Checklist
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(10, 8, "ID", 1, 0, 'C')
    pdf.cell(120, 8, "Question", 1, 0, 'C')
    pdf.cell(15, 8, "Res", 1, 0, 'C')
    pdf.cell(45, 8, "Comments", 1, 1, 'C')
    
    pdf.set_font("Arial", '', 8)
    for q in QA_CHECKLIST:
        q_id = str(q['id'])
        res = report_data['responses'].get(q_id, "N/A")
        comment = report_data['comments'].get(q_id, "")
        
        # Handle long text wrapping for comments
        pdf.cell(10, 8, str(q['id']), 1, 0, 'C')
        
        # Question text (truncated if too long for single cell, or use multi_cell logic)
        # For simplicity in standard FPDF, we'll use a fixed height cell
        q_text = q['text'][:80] + "..." if len(q['text']) > 80 else q['text']
        pdf.cell(120, 8, q_text, 1, 0, 'L')
        
        pdf.cell(15, 8, res, 1, 0, 'C')
        pdf.cell(45, 8, comment[:30] + "..." if len(comment) > 30 else comment, 1, 1, 'L')

    return pdf.output()

# ==========================================
# STREAMLIT UI
# ==========================================

st.set_page_config(page_title="Sparta Telecom QA", layout="wide")
st.title("📞 Sparta Telecom Quality Assurance App")

# Sidebar Navigation
menu = st.sidebar.radio("Navigation", ["📝 New QA Evaluation", "📊 View Records & Export", "🏆 Agent Performance"])

if menu == "📝 New QA Evaluation":
    st.header("New QA Evaluation")
    
    with st.form("qa_form"):
        col1, col2 = st.columns(2)
        with col1:
            call_date = st.date_input("Date of Call", date.today())
            agent_name = st.text_input("Agent Name")
            evaluator_name = st.text_input("Evaluator Name")
        with col2:
            call_id = st.text_input("Call Reference / ID")
            customer_name = st.text_input("Customer Name")
            
        st.markdown("---")
        st.subheader("QA Checklist")
        
        responses = {}
        comments = {}
        
        # Grouping questions slightly for better UI, or just listing them
        for q in QA_CHECKLIST:
            col_q, col_r, col_c = st.columns([4, 1, 3])
            with col_q:
                fatal_tag = "🔴 **FATAL**" if q['fatal'] else ""
                st.markdown(f"**{q['id']}.** {q['text']} {fatal_tag}")
            with col_r:
                responses[str(q['id'])] = st.radio("Ans", ["Yes", "No"], key=f"q_{q['id']}", label_visibility="collapsed", horizontal=True)
            with col_c:
                comments[str(q['id'])] = st.text_input("Comments", key=f"c_{q['id']}", label_visibility="collapsed", placeholder="Add notes...")

        submitted = st.form_submit_button("Submit Evaluation", type="primary")
        
        if submitted:
            if not agent_name or not call_id:
                st.error("Please fill in Agent Name and Call Reference.")
            else:
                score, fatal_fail, fatal_ids = calculate_score(responses)
                
                # Prepare record
                record = {
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Call_Date": call_date.strftime("%Y-%m-%d"),
                    "Call_ID": call_id,
                    "Agent_Name": agent_name,
                    "Customer_Name": customer_name,
                    "Evaluator": evaluator_name,
                    "Score": score,
                    "Fatal_Fail": fatal_fail,
                    "Fatal_Questions_Failed": str(fatal_ids) if fatal_ids else "None"
                }
                
                # Add individual Q responses and comments to the record
                for q in QA_CHECKLIST:
                    q_id = str(q['id'])
                    record[f"Q{q_id}_Ans"] = responses[q_id]
                    record[f"Q{q_id}_Comment"] = comments[q_id]
                    
                if save_to_database(record):
                    st.success(f"Evaluation Saved! Final Score: **{score}%**")
                    if fatal_fail:
                        st.error(f"🚨 AUTO-FAIL: Fatal errors on questions: {fatal_ids}")
                    
                    # Offer PDF Download
                    report_data = {**record, "responses": responses, "comments": comments}
                    pdf_bytes = generate_pdf(report_data)
                    st.download_button(
                        label="📄 Download PDF Report",
                        data=pdf_bytes,
                        file_name=f"QA_Report_{call_id}.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.error("Failed to save. Is the Excel file open elsewhere?")

elif menu == "📊 View Records & Export":
    st.header("View Records & Export Reports")
    
    df = load_database()
    
    if df.empty:
        st.info("No records found. Submit a new evaluation first!")
    else:
        # Filters
        col1, col2 = st.columns(2)
        with col1:
            filter_agent = st.multiselect("Filter by Agent", options=df['Agent_Name'].unique())
        with col2:
            filter_date = st.date_input("Filter by Date", value=[])
            
        # Apply filters
        filtered_df = df.copy()
        if filter_agent:
            filtered_df = filtered_df[filtered_df['Agent_Name'].isin(filter_agent)]
        if len(filter_date) == 2:
            start_date, end_date = filter_date
            filtered_df['Call_Date'] = pd.to_datetime(filtered_df['Call_Date'])
            filtered_df = filtered_df[(filtered_df['Call_Date'] >= pd.to_datetime(start_date)) & 
                                      (filtered_df['Call_Date'] <= pd.to_datetime(end_date))]
                                      
        st.dataframe(filtered_df, use_container_width=True)
        
        # Export Buttons
        col1, col2 = st.columns(2)
        with col1:
            # Excel Export
            excel_io = io.BytesIO()
            filtered_df.to_excel(excel_io, index=False)
            st.download_button(
                label="📊 Download Filtered Excel",
                data=excel_io.getvalue(),
                file_name="QA_Records_Export.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        with col2:
            # PDF Export (Generates a combined PDF or single selected)
            st.info("Select a Call ID from the table above to generate a specific PDF, or use the main evaluation page for instant PDFs.")

elif menu == "🏆 Agent Performance":
    st.header("Agent Performance Dashboard")
    
    df = load_database()
    if df.empty:
        st.info("No records found.")
    else:
        # Aggregate by Agent
        agent_stats = df.groupby('Agent_Name').agg(
            Total_Calls=('Call_ID', 'count'),
            Avg_Score=('Score', 'mean'),
            Auto_Fails=('Fatal_Fail', 'sum')
        ).reset_index()
        
        agent_stats['Avg_Score'] = agent_stats['Avg_Score'].round(2)
        agent_stats['Pass_Rate'] = ((agent_stats['Total_Calls'] - agent_stats['Auto_Fails']) / agent_stats['Total_Calls'] * 100).round(2)
        
        st.dataframe(agent_stats, use_container_width=True)
        
        # Visuals
        col1, col2 = st.columns(2)
        with col1:
            st.bar_chart(agent_stats.set_index('Agent_Name')['Avg_Score'], color="#00cc00")
            st.caption("Average Quality Score by Agent")
        with col2:
            st.bar_chart(agent_stats.set_index('Agent_Name')['Auto_Fails'], color="#ff0000")
            st.caption("Total Auto-Fails (Fatal Errors) by Agent")
