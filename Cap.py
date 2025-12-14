import streamlit as st
import pandas as pd
import time
import os
from pathlib import Path

# Folder where Cap.py lives
ROOT_DIR = Path(__file__).resolve().parent
# Full path to your Excel database (database.xlsx must sit next to Cap.py)
EXCEL_FILE = ROOT_DIR / "database.xlsx"
TRANSACTIONS_SHEET = "Transactions"


st.set_page_config(page_title="Aggie Access 2.0", layout="wide")
st.caption(f"Using database file at: {EXCEL_FILE.resolve()}")

def load_transactions():
    """
    Load the Transactions sheet from database.xlsx.
    If the sheet doesn't exist yet, return an empty DataFrame with the right columns.
    """
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name=TRANSACTIONS_SHEET, engine="openpyxl")
        df.columns = df.columns.str.strip()
        return df
    except FileNotFoundError:
        return pd.DataFrame(
            columns=[
                "Username",
                "Role",
                "Type",
                "Amount",
                "Old_Balance",
                "New_Balance",
                "Timestamp",
            ]
        )
    except ValueError:
        # Workbook exists but Transactions sheet does not
        return pd.DataFrame(
            columns=[
                "Username",
                "Role",
                "Type",
                "Amount",
                "Old_Balance",
                "New_Balance",
                "Timestamp",
            ]
        )


def save_students_and_transactions(students_df: pd.DataFrame, transactions_df: pd.DataFrame):
    """
    Save updated Students and Transactions sheets back to database.xlsx.
    Other sheets (Faculty, Messages, etc.) are left alone.
    """
    with pd.ExcelWriter(
        EXCEL_FILE,
        engine="openpyxl",
        mode="a",               # append to existing workbook
        if_sheet_exists="replace",  # only replace these two sheets
    ) as writer:
        students_df.to_excel(writer, sheet_name="Students", index=False)
        transactions_df.to_excel(writer, sheet_name=TRANSACTIONS_SHEET, index=False)




# --- Load Data ---

def load_student_data():
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name="Students", engine="openpyxl")
        df.columns = df.columns.str.strip().str.replace(" ", "_")
        return df
    except Exception as e:
        st.error(f"Error loading Students sheet: {e}")
        return pd.DataFrame()


def load_faculty_data():
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name="Faculty", engine="openpyxl")
        df.columns = df.columns.str.strip().str.replace(" ", "_")
        return df
    except Exception as e:
        st.error(f"Error loading Faculty sheet: {e}")
        return pd.DataFrame()


def load_messages():
    try:
        df = pd.read_excel(EXCEL_FILE, sheet_name="Messages", engine="openpyxl")
        df.columns = df.columns.str.strip().str.replace(" ", "_")
        return df
    except Exception as e:
        # Sheet not found or error -> start with empty structure
        return pd.DataFrame(columns=["Sender", "Receiver", "Message", "Timestamp"])

# --- Save Data ---
def save_student_data(df):
    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        df.to_excel(writer, sheet_name="Students", index=False)
    # Keep the updated DataFrame in memory
    st.session_state["student_data"] = df

def save_faculty_data(df):
    with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        df.to_excel(writer, sheet_name="Faculty", index=False)
    # Keep the updated DataFrame in memory
    st.session_state["faculty_data"] = df


def save_message(sender, receiver, text):
    if not text or not str(text).strip():
        st.error("Message cannot be empty.")
        return
    try:
        messages_df = load_messages()
        messages_df = pd.concat(
            [messages_df, pd.DataFrame({
                "Sender": [sender],
                "Receiver": [receiver],
                "Message": [text],
                "Timestamp": [pd.Timestamp.now()]
            })],
            ignore_index=True
        )
        with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            messages_df.to_excel(writer, sheet_name="Messages", index=False)

        # Store a global notice so dashboards can show it at the top
        st.session_state["last_message_notice"] = f"Message sent to {receiver}."
        st.success(st.session_state["last_message_notice"])
        st.rerun()
    except Exception as e:
        st.error(f"Error saving message: {e}")







# --- Initialize Session State ---
if "student_data" not in st.session_state:
    st.session_state["student_data"] = load_student_data()
if "faculty_data" not in st.session_state:
    st.session_state["faculty_data"] = load_faculty_data()
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "show_welcome" not in st.session_state:
    st.session_state["show_welcome"] = False

# --- Login Function ---
def login():
    st.title("🎓 Aggie Access 2.0 Login")

    roles = ["Student", "Faculty"]
    selected_role = st.selectbox("Select your role", roles, key="login_role")

    # Show / hide password toggle
    show_password = st.checkbox("Show password", key="login_show_password")
    # Streamlit expects "default" for plain text, not "text"
    password_type = "default" if show_password else "password"

    # Explicit keys so Streamlit + browser autofill behave better
    username_input = st.text_input("Username", key="login_username")
    password_input = st.text_input("Password", type=password_type, key="login_password")

    login_btn = st.button("Login", use_container_width=True, key="login_button")

    if login_btn:
        # Normalize what the user / browser filled in
        username = username_input.strip()
        password = password_input.strip()

        # Pick the correct sheet
        df = (
            st.session_state["student_data"]
            if selected_role.lower() == "student"
            else st.session_state["faculty_data"]
        )

        # Basic safety checks
        if "Username" not in df.columns:
            st.error("No 'Username' column found in the selected sheet.")
            return
        if "Password" not in df.columns:
            st.error("No 'Password' column found in the selected sheet.")
            return

        # Normalize usernames from the sheet
        username_series = df["Username"].astype(str).str.strip()
        match_mask = username_series == username

        if match_mask.any():
            user_row = df[match_mask].iloc[0]

            # Normalize stored password too
            stored_password = str(user_row["Password"]).strip()

            if password == stored_password:
                st.session_state["logged_in"] = True
                st.session_state["role"] = selected_role
                st.session_state["username"] = username
                st.session_state["user_data"] = user_row.to_dict()
                st.session_state["show_welcome"] = True
                st.success("Login successful.")
                st.rerun()
            else:
                st.error("Incorrect password.")
        else:
            st.error("Username not found.")


    


def user_management():
    st.markdown("---")
    st.subheader("User management")

    with st.expander("Add, edit, or delete users"):
        action = st.selectbox(
            "Choose an action",
            ["Add new user", "Edit existing user", "Delete user"],
            key="user_mgmt_action"
        )

        # ---------- ADD NEW USER ----------
        if action == "Add new user":
            new_role = st.selectbox("New user role", ["Student", "Faculty"], key="mgmt_new_role")
            new_username = st.text_input("New username", key="mgmt_new_username")
            new_password = st.text_input("Temporary password", type="password", key="mgmt_new_password")
            new_full_name = st.text_input("Full name", key="mgmt_new_full_name")

            if new_role == "Student":
                new_major = st.text_input("Major", key="mgmt_new_major")
                new_gpa = st.number_input(
                    "Starting GPA",
                    min_value=0.0,
                    max_value=4.0,
                    value=0.0,
                    step=0.01,
                    key="mgmt_new_gpa",
                    help="Enter GPA on a 0.0–4.0 scale, for example 3.25.",
)

                new_email = st.text_input("Email", key="mgmt_new_student_email")
                new_advisor_assigned = st.text_input("Advisor Assigned (number/name)", key="mgmt_new_student_advisor")
                new_course_registered = st.text_input("Course Registered", key="mgmt_new_student_course")

                if st.button("Create Student Account", key="mgmt_create_student"):
                    student_df = st.session_state["student_data"].copy()

                    if "Username" not in student_df.columns:
                        st.error("Students sheet has no 'Username' column.")
                    elif new_username in student_df["Username"].astype(str).values:
                        st.error("That username already exists in Students.")
                    else:
                        new_row = {col: "" for col in student_df.columns}
                        if "Username" in new_row: new_row["Username"] = new_username
                        if "Password" in new_row: new_row["Password"] = new_password
                        if "Full_Name" in new_row: new_row["Full_Name"] = new_full_name
                        if "Major" in new_row: new_row["Major"] = new_major
                        if "GPA" in new_row: new_row["GPA"] = new_gpa
                        if "Email" in new_row: new_row["Email"] = new_email
                        if "Advisor_Assigned" in new_row: new_row["Advisor_Assigned"] = new_advisor_assigned
                        if "Course_Registered" in new_row: new_row["Course_Registered"] = new_course_registered

                        student_df = pd.concat([student_df, pd.DataFrame([new_row])], ignore_index=True)
                        save_student_data(student_df)
                        st.success("New student account created!")

            else:  # Faculty
                new_course = st.text_input("Course", key="mgmt_new_course")
                new_schedule = st.text_input("Schedule", key="mgmt_new_schedule")
                new_advisor_number = st.text_input("Advisor Number", key="mgmt_new_fac_adv")
                new_email = st.text_input("Email", key="mgmt_new_fac_email")

                if st.button("Create Faculty Account", key="mgmt_create_faculty"):
                    faculty_df = st.session_state["faculty_data"].copy()

                    if "Username" not in faculty_df.columns:
                        st.error("Faculty sheet has no 'Username' column.")
                    elif new_username in faculty_df["Username"].astype(str).values:
                        st.error("That username already exists in Faculty.")
                    else:
                        new_row = {col: "" for col in faculty_df.columns}
                        if "Username" in new_row: new_row["Username"] = new_username
                        if "Password" in new_row: new_row["Password"] = new_password
                        if "Full_Name" in new_row: new_row["Full_Name"] = new_full_name
                        if "Course" in new_row: new_row["Course"] = new_course
                        if "Schedule" in new_row: new_row["Schedule"] = new_schedule
                        if "Advisor_Number" in new_row: new_row["Advisor_Number"] = new_advisor_number
                        if "Email" in new_row: new_row["Email"] = new_email

                        faculty_df = pd.concat([faculty_df, pd.DataFrame([new_row])], ignore_index=True)
                        save_faculty_data(faculty_df)
                        st.success("New faculty account created!")

        # ---------- EDIT EXISTING USER ----------
        elif action == "Edit existing user":
            update_role = st.selectbox("Select role to update", ["Student", "Faculty"], key="mgmt_update_role")

            if update_role == "Student":
                student_df = st.session_state["student_data"]
                if "Username" in student_df.columns and not student_df.empty:
                    student_usernames = student_df["Username"].astype(str).tolist()
                    selected_student = st.selectbox("Select student username", student_usernames, key="mgmt_update_student_username")

                    if selected_student:
                        row = student_df[student_df["Username"] == selected_student].iloc[0]

                        upd_full_name = st.text_input("Full Name", value=str(row.get("Full_Name", "")), key="mgmt_upd_student_full_name")
                        upd_major = st.text_input("Major", value=str(row.get("Major", "")), key="mgmt_upd_student_major")
                        upd_gpa = st.number_input(
                            
                            "GPA",
                            min_value=0.0,
                            max_value=4.0,
                            value=float(row.get("GPA", 0.0)),
                            step=0.01,
                            key="mgmt_upd_student_gpa",
                        )
                        upd_email = st.text_input("Email", value=str(row.get("Email", "")), key="mgmt_upd_student_email")
                        upd_advisor = st.text_input("Advisor Assigned", value=str(row.get("Advisor_Assigned", "")), key="mgmt_upd_student_adv")
                        upd_courses = st.text_input("Course Registered", value=str(row.get("Course_Registered", "")), key="mgmt_upd_student_courses")

                        if st.button("Save Student Changes", key="mgmt_btn_save_student_update"):
                            idx = student_df[student_df["Username"] == selected_student].index[0]
                            if "Full_Name" in student_df.columns:
                                student_df.loc[idx, "Full_Name"] = upd_full_name
                            if "Major" in student_df.columns:
                                student_df.loc[idx, "Major"] = upd_major
                            if "GPA" in student_df.columns:
                                student_df.loc[idx, "GPA"] = upd_gpa
                            if "Email" in student_df.columns:
                                student_df.loc[idx, "Email"] = upd_email
                            if "Advisor_Assigned" in student_df.columns:
                                student_df.loc[idx, "Advisor_Assigned"] = upd_advisor
                            if "Course_Registered" in student_df.columns:
                                student_df.loc[idx, "Course_Registered"] = upd_courses

                            save_student_data(student_df)
                            st.success(f"Student '{selected_student}' updated successfully!")

            else:  # Faculty
                faculty_df = st.session_state["faculty_data"]
                if "Username" in faculty_df.columns and not faculty_df.empty:
                    faculty_usernames = faculty_df["Username"].astype(str).tolist()
                    selected_faculty = st.selectbox("Select faculty username", faculty_usernames, key="mgmt_update_faculty_username")

                    if selected_faculty:
                        row = faculty_df[faculty_df["Username"] == selected_faculty].iloc[0]

                        upd_full_name = st.text_input("Full Name", value=str(row.get("Full_Name", "")), key="mgmt_upd_faculty_full_name")
                        upd_course = st.text_input("Course", value=str(row.get("Course", "")), key="mgmt_upd_faculty_course")
                        upd_schedule = st.text_input("Schedule", value=str(row.get("Schedule", "")), key="mgmt_upd_faculty_schedule")
                        upd_email = st.text_input("Email", value=str(row.get("Email", "")), key="mgmt_upd_faculty_email")
                        upd_adv_num = st.text_input("Advisor Number", value=str(row.get("Advisor_Number", "")), key="mgmt_upd_faculty_adv_num")

                        if st.button("Save Faculty Changes", key="mgmt_btn_save_faculty_update"):
                            idx = faculty_df[faculty_df["Username"] == selected_faculty].index[0]
                            if "Full_Name" in faculty_df.columns:
                                faculty_df.loc[idx, "Full_Name"] = upd_full_name
                            if "Course" in faculty_df.columns:
                                faculty_df.loc[idx, "Course"] = upd_course
                            if "Schedule" in faculty_df.columns:
                                faculty_df.loc[idx, "Schedule"] = upd_schedule
                            if "Email" in faculty_df.columns:
                                faculty_df.loc[idx, "Email"] = upd_email
                            if "Advisor_Number" in faculty_df.columns:
                                faculty_df.loc[idx, "Advisor_Number"] = upd_adv_num

                            save_faculty_data(faculty_df)
                            st.success(f"Faculty '{selected_faculty}' updated successfully!")

        # ---------- DELETE USER ----------
        else:  # "Delete user"
            delete_role = st.selectbox("Delete from", ["Student", "Faculty"], key="mgmt_delete_role")

            if delete_role == "Student":
                student_df = st.session_state["student_data"]
                if "Username" in student_df.columns and not student_df.empty:
                    student_usernames = student_df["Username"].astype(str).tolist()
                    del_student = st.selectbox("Select student to delete", student_usernames, key="mgmt_delete_student_username")
                    confirm_del_student = st.checkbox(
                        "I understand this will permanently remove the student record.",
                        key="mgmt_confirm_del_student"
                    )

                    if st.button("Delete Student", key="mgmt_btn_delete_student") and del_student and confirm_del_student:
                        student_df = student_df[student_df["Username"] != del_student].reset_index(drop=True)
                        save_student_data(student_df)
                        st.success(f"Student '{del_student}' deleted successfully!")

            else:  # Faculty
                faculty_df = st.session_state["faculty_data"]
                if "Username" in faculty_df.columns and not faculty_df.empty:
                    faculty_usernames = faculty_df["Username"].astype(str).tolist()
                    del_faculty = st.selectbox("Select faculty to delete", faculty_usernames, key="mgmt_delete_faculty_username")
                    confirm_del_faculty = st.checkbox(
                        "I understand this will permanently remove the faculty record.",
                        key="mgmt_confirm_del_faculty"
                    )

                    if st.button("Delete Faculty", key="mgmt_btn_delete_faculty") and del_faculty and confirm_del_faculty:
                        faculty_df = faculty_df[faculty_df["Username"] != del_faculty].reset_index(drop=True)
                        save_faculty_data(faculty_df)
                        st.success(f"Faculty '{del_faculty}' deleted successfully!")

# --- Student Dashboard ---
def student_dashboard(user_data):
    st.subheader("🎓 Student Dashboard")
    st.title("Student Dashboard")
    st.write(f"Welcome, {user_data.get('Full_Name', st.session_state.get('username', 'Student'))}!")


    # --- Advisor Card ---
    advisor_name = user_data.get("Advisor_Assigned") or user_data.get("Advisor") or None

    if advisor_name:
        st.markdown("### Your Advisor")

        faculty_df = st.session_state.get("faculty_data")
        advisor_email = None

        if isinstance(faculty_df, pd.DataFrame):
            # Try to find advisor by full name
            match = faculty_df[
                faculty_df["Full_Name"].astype(str).str.strip() == str(advisor_name).strip()
            ]
            if not match.empty:
                row = match.iloc[0]
                advisor_email = str(row.get("Email", "")).strip() or None

        # Show card
        col_adv1, col_adv2 = st.columns([3, 2])
        with col_adv1:
            st.write(f"**Name:** {advisor_name}")
        with col_adv2:
            if advisor_email:
                st.write(f"**Email:** {advisor_email}")
            else:
                st.write("**Email:** (not listed)")
        st.caption("You can contact your advisor for help with courses, grades, or graduation plans.")

    # --- Global notifications (finance + messaging) ---
    if st.session_state.get("last_finance_message"):
        st.success(st.session_state["last_finance_message"])
    if st.session_state.get("last_message_notice"):
        st.info(st.session_state["last_message_notice"])

    # 📬 Message count badge
    messages_df = load_messages()
    if not messages_df.empty:
        inbox_count = (messages_df["Receiver"] == user_data["Full_Name"]).sum()
        sent_count = (messages_df["Sender"] == user_data["Full_Name"]).sum()
        st.caption(f"📨 Messages – Inbox: {inbox_count} | Sent: {sent_count}")
    else:
        st.caption("📨 Messages – Inbox: 0 | Sent: 0")

    # Build course list once
    if "Course_Registered" in user_data and pd.notna(user_data["Course_Registered"]):
        courses = [c.strip() for c in str(user_data["Course_Registered"]).split(",") if c.strip()]
    else:
        courses = []

    # Stable section selector (doesn't reset like buttons)
    section = st.radio(
        "Select section",
        ["Academic", "Finance", "Advising", "Messaging"],
        horizontal=True,
        key="student_section"
    )

    # ========== Academic ==========
    if section == "Academic":
        st.markdown("### Academic Information")
        st.write(f"**Major:** {user_data['Major']}")
        st.write(f"**Transcript Level:** {user_data['Transcript_Level']}")
        st.write(f"**GPA:** {user_data['GPA']}")
        st.write(f"**Attendance:** {user_data['Attendance']}")
        st.write(f"**Status:** {user_data['Full_Time/Part_Time']}")
        st.write(f"**Qualification:** {user_data['Qualification']}")
        st.write(f"**Courses Registered:** {', '.join(courses)}")

    # ========== Finance ==========
    elif section == "Finance":
        st.subheader("Finance")

        students_df = st.session_state["student_data"].copy()

        # Make sure required columns exist
        if "Username" not in students_df.columns or "Account_Balance" not in students_df.columns:
            st.error("The Students sheet must have 'Username' and 'Account_Balance' columns.")
        else:
            username = st.session_state.get("username", "")
            role = st.session_state.get("role", "Student")

            # Find the logged-in student's row
            mask = students_df["Username"].astype(str).str.strip() == str(username).strip()
            if not mask.any():
                st.error("Could not find your record in the Students sheet.")
            else:
                # Current balance
                current_balance = pd.to_numeric(
                    students_df.loc[mask, "Account_Balance"],
                    errors="coerce"
                ).iloc[0]
                if pd.isna(current_balance):
                    current_balance = 0.0

                st.metric("Current Balance", f"${current_balance:,.2f}")

                col1, col2 = st.columns(2)

                # --- Deposit column ---
                with col1:
                    deposit_amount = st.number_input(
                        "Deposit amount",
                        min_value=0.0,
                        step=10.0,
                        key="deposit_amount",
                    )
                    if st.button("Make Deposit", key="deposit_button"):
                        if deposit_amount > 0:
                            new_balance = current_balance + deposit_amount

                            # Update in-memory DataFrame
                            students_df.loc[mask, "Account_Balance"] = new_balance
                            st.session_state["student_data"] = students_df

                            # Append to Transactions sheet
                            tx_df = load_transactions()
                            new_row = {
                                "Username": username,
                                "Role": role,
                                "Type": "Deposit",
                                "Amount": float(deposit_amount),
                                "Old_Balance": float(current_balance),
                                "New_Balance": float(new_balance),
                                "Timestamp": pd.Timestamp.now(),
                            }
                            tx_df = pd.concat(
                                [tx_df, pd.DataFrame([new_row])],
                                ignore_index=True,
                            )

                            # Save both Students + Transactions back to Excel
                            save_students_and_transactions(students_df, tx_df)

                            st.success("Deposit successful. Your new balance has been saved.")
                            st.rerun()
                        else:
                            st.warning("Enter a deposit amount greater than 0.")

                # --- Withdraw column ---
                with col2:
                    withdraw_amount = st.number_input(
                        "Withdraw amount",
                        min_value=0.0,
                        step=10.0,
                        key="withdraw_amount",
                    )
                    if st.button("Withdraw", key="withdraw_button"):
                        if withdraw_amount > 0:
                            if withdraw_amount > current_balance:
                                st.error("Cannot withdraw more than your current balance.")
                            else:
                                new_balance = current_balance - withdraw_amount

                                # Update in-memory DataFrame
                                students_df.loc[mask, "Account_Balance"] = new_balance
                                st.session_state["student_data"] = students_df

                                # Append to Transactions sheet
                                tx_df = load_transactions()
                                new_row = {
                                    "Username": username,
                                    "Role": role,
                                    "Type": "Withdrawal",
                                    "Amount": float(withdraw_amount),
                                    "Old_Balance": float(current_balance),
                                    "New_Balance": float(new_balance),
                                    "Timestamp": pd.Timestamp.now(),
                                }
                                tx_df = pd.concat(
                                    [tx_df, pd.DataFrame([new_row])],
                                    ignore_index=True,
                                )

                                # Save both Students + Transactions back to Excel
                                save_students_and_transactions(students_df, tx_df)

                                st.success("Withdrawal successful. Your new balance has been saved.")
                                st.rerun()
                        else:
                            st.warning("Enter a withdrawal amount greater than 0.")

                # --- Recent transactions table ---
                tx_df = load_transactions()
                tx_user = tx_df[
                    tx_df["Username"].astype(str).str.strip() == str(username).strip()
                ]

                if not tx_user.empty:
                    st.markdown("#### Recent Transactions")
                    tx_user = tx_user.sort_values("Timestamp", ascending=False).head(5)
                    st.dataframe(
                        tx_user[["Timestamp", "Type", "Amount", "Old_Balance", "New_Balance"]],
                        use_container_width=True,
                    )
                else:
                    st.info("No transactions recorded yet.")


    # ========== Advising ==========
    elif section == "Advising":
        st.markdown("### Advising Information")
        faculty_df = st.session_state["faculty_data"]
        advisor_number = user_data['Advisor_Assigned']
        advisor_row = faculty_df[faculty_df['Advisor_Number'] == advisor_number]
        if not advisor_row.empty:
            advisor_name = advisor_row['Full_Name'].values[0]
            advisor_email = advisor_row['Email'].values[0]
        else:
            advisor_name, advisor_email = "Not Found", "Not Found"
        st.write(f"**Advisor Name:** {advisor_name}")
        st.write(f"**Advisor Email:** {advisor_email}")
        message = st.text_area("Send a message to your advisor:")
        if st.button("Send Message to Advisor"):
            save_message(sender=user_data['Full_Name'], receiver=advisor_name, text=message)

    # ========== Messaging ==========
    elif section == "Messaging":
        st.markdown("### Messaging to Advisors")
        faculty_df = st.session_state["faculty_data"]

        selected_advisor = st.selectbox("Select Advisor", faculty_df['Full_Name'].tolist())
        message_text = st.text_area("Enter your message:")
        if st.button("Send Message"):
            save_message(sender=user_data['Full_Name'], receiver=selected_advisor, text=message_text)

        messages_df = load_messages()

        if not messages_df.empty:
            # Inbox
            st.markdown("#### Inbox")
            inbox = messages_df[messages_df["Receiver"] == user_data["Full_Name"]].sort_values("Timestamp", ascending=False)
            if inbox.empty:
                st.info("No messages received yet.")
            else:
                for _, row in inbox.iterrows():
                    st.write(f"**From:** {row['Sender']}  |  **At:** {row['Timestamp']}")
                    st.write(row["Message"])
                    st.markdown("---")

            # Sent
            st.markdown("#### Sent")
            sent = messages_df[messages_df["Sender"] == user_data["Full_Name"]].sort_values("Timestamp", ascending=False)
            if sent.empty:
                st.info("No messages sent yet.")
            else:
                for _, row in sent.iterrows():
                    st.write(f"**To:** {row['Receiver']}  |  **At:** {row['Timestamp']}")
                    st.write(row["Message"])
                    st.markdown("---")
        else:
            st.info("No messages in the system yet.")


def faculty_dashboard(user_data):
    st.subheader("👨‍🏫 Faculty Dashboard")

    # --- Global messaging notification (set in save_message) ---
    if st.session_state.get("last_message_notice"):
        st.info(st.session_state["last_message_notice"])

    # 📬 Message count badge
    messages_df = load_messages()
    if not messages_df.empty:
        inbox_count = (messages_df["Receiver"] == user_data["Full_Name"]).sum()
        sent_count = (messages_df["Sender"] == user_data["Full_Name"]).sum()
        st.caption(f"📨 Messages – Inbox: {inbox_count} | Sent: {sent_count}")
    else:
        st.caption("📨 Messages – Inbox: 0 | Sent: 0")

    # Stable section selector
    section = st.radio(
        "Select section",
        ["Instructor Info", "Advisees", "Messaging"],
        horizontal=True,
        key="faculty_section"
    )

    # ========== Instructor Info ==========
    if section == "Instructor Info":
        st.markdown("### Instructor Information")
        st.write(f"**Course:** {user_data.get('Course', '')}")
        st.write(f"**Schedule:** {user_data.get('Schedule', '')}")
        st.write(f"**Advisor Number:** {user_data.get('Advisor_Number', '')}")
        st.write(f"**Email:** {user_data.get('Email', '')}")

    # ========== Advisees / GPA ==========
    elif section == "Advisees":
        st.markdown("### Manage Student GPA")
        student_df = st.session_state["student_data"]
        # show students registered in this faculty member's course, if the column exists
        if "Course_Registered" in student_df.columns:
            course_students = student_df[
                student_df["Course_Registered"].astype(str).str.contains(
                    str(user_data.get("Course", "")), na=False
                )
            ]
        else:
            course_students = student_df.iloc[0:0]  # empty

        if not course_students.empty:
            for idx, row in course_students.iterrows():
                st.write(f"**Student:** {row.get('Full_Name', '')} | Current GPA: {row.get('GPA', '')}")
                new_gpa = st.number_input(
                    f"Update GPA for {row.get('Full_Name', '')}",
                    min_value=0.0, max_value=4.0,
                    value=float(row.get('GPA', 0.0) or 0.0),
                    step=0.01,
                    key=f"gpa_{row.get('Username', idx)}"
                )
                if st.button(f"Save GPA for {row.get('Full_Name', '')}", key=f"save_{row.get('Username', idx)}"):
                    student_df.loc[idx, 'GPA'] = new_gpa
                    save_student_data(student_df)
                    st.success(f"GPA updated for {row.get('Full_Name', '')}!")
        else:
            st.info("No students registered for your course, or Course_Registered column missing.")

    # ========== Messaging ==========
    elif section == "Messaging":
        st.markdown("### Messages")

        students_df = st.session_state["student_data"]
        if "Full_Name" in students_df.columns and not students_df.empty:
            student_to_message = st.selectbox("Select a student to message", students_df['Full_Name'].tolist())
        else:
            student_to_message = None
            st.info("No students available to message.")

        message_text = st.text_area("Enter your message:")
        if st.button("Send Message to Student") and student_to_message:
            save_message(sender=user_data['Full_Name'], receiver=student_to_message, text=message_text)

        messages_df = load_messages()

        if not messages_df.empty:
            # Inbox
            st.markdown("#### Inbox")
            inbox = messages_df[messages_df["Receiver"] == user_data["Full_Name"]].sort_values("Timestamp", ascending=False)
            if inbox.empty:
                st.info("No messages received yet.")
            else:
                for _, row in inbox.iterrows():
                    st.write(f"**From:** {row['Sender']}  |  **At:** {row['Timestamp']}")
                    st.write(row["Message"])
                    st.markdown("---")

            # Sent
            st.markdown("#### Sent")
            sent = messages_df[messages_df["Sender"] == user_data["Full_Name"]].sort_values("Timestamp", ascending=False)
            if sent.empty:
                st.info("No messages sent yet.")
            else:
                for _, row in sent.iterrows():
                    st.write(f"**To:** {row['Receiver']}  |  **At:** {row['Timestamp']}")
                    st.write(row["Message"])
                    st.markdown("---")
        else:
            st.info("No messages in the system yet.")

    

# --- Main App ---
def main():
    # --- Initialize session state defaults ---
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "show_welcome" not in st.session_state:
        st.session_state["show_welcome"] = False

    if not st.session_state["logged_in"]:
        login()
    else:
        user_data = st.session_state["user_data"]
        role = st.session_state["role"]

        if st.session_state["show_welcome"]:
            st.title("Aggie Access 2.0")
            st.write("Welcome to your dashboard.")
            if st.button("Continue to Dashboard"):
                st.session_state["show_welcome"] = False
                st.rerun()
        else:
            # Logged-in banner + logout
            st.markdown(
                f"<div style='position:absolute; top:10px; right:20px;'>"
                f"👤 Logged in as: <b>{user_data['Full_Name']}</b> ({role})"
                f"</div>",
                unsafe_allow_html=True
            )
            if st.button("Log Out", type="primary"):
                st.session_state.clear()
                st.rerun()

            # Route based on role
            if role.lower() == "student":
                student_dashboard(user_data)
            else:
                faculty_dashboard(user_data)

            # Show user management tools after any successful login
            if "user_management" in globals():
                user_management()

            

if __name__ == "__main__":
    main()

