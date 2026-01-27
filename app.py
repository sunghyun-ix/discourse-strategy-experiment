import streamlit as st
from openai import OpenAI
import time
import random

# [SECURITY] Get keys from Streamlit Secrets
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
    ASST_ID_A = st.secrets["ASST_ID_A"]
    ASST_ID_B = st.secrets["ASST_ID_B"]
else:
    st.error("Error: Secrets are not set. Please add them in Streamlit Cloud settings.")
    st.stop()

client = OpenAI(api_key=api_key)

st.set_page_config(page_title="Sci-Fi Experiment", page_icon="🧪", layout="wide")

# [CSS STYLING]
st.markdown("""
    <style>
    .main-title { font-size: 3rem; font-weight: 700; text-align: center; color: #1E1E1E; margin-bottom: 10px; }
    .welcome-box { background-color: #f0f2f6; padding: 30px; border-radius: 15px; text-align: center; margin-bottom: 30px; border: 1px solid #e0e0e0; }
    .welcome-text { font-size: 1.5rem; font-weight: 600; color: #333; }
    .instruction-text { font-size: 1.1rem; color: #555; margin-top: 15px; }
    .highlight { color: #FF4B4B; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# [SIDEBAR] Admin Panel (Password Protected)
# =========================================================
with st.sidebar:
    st.title("🛡️ Admin Panel")
    
    # 1. participant ID 
    participant_id = st.text_input("Participant ID", value="P01")
    
    st.divider()
    
    # 2. experiment manager access password 
    st.markdown("### 🔒 Researcher Access")
    admin_pass = st.text_input("Enter Password to Unlock", type="password")

    # 3. right password and pop up admin controls 
    if admin_pass == "1357":  
        st.success("Admin Mode Unlocked! 🔓")
        
        # (1) reset session for new participants 
        if st.button("🔄 Reset for New Participant", type="primary"):
            st.session_state.clear()
            st.rerun()
            
        st.divider()

        # (2) assigned condition display 
        if "assigned_condition" not in st.session_state:
            st.session_state.assigned_condition = random.choice(["Condition A", "Condition B"])
        
        # (3) condition confirmation and manual override 
        st.write(f"**Current Condition:**")
        st.info(f"{st.session_state.assigned_condition}")
        
        change_cond = st.checkbox("Manual Override")
        if change_cond:
            st.session_state.assigned_condition = st.radio("Force Condition:", ("Condition A", "Condition B"))

        st.divider()

        # (4) log download 
        if st.button("💾 Download Log"):
            if "messages" in st.session_state:
                log_text = f"Participant ID: {participant_id}\nCondition: {st.session_state.assigned_condition}\n" + "="*30 + "\n\n"
                for msg in st.session_state.messages:
                    log_text += f"[{msg['role'].upper()}]\n{msg['content']}\n\n"
                file_name = f"{participant_id}_{st.session_state.assigned_condition.replace(' ', '')}_Log.txt"
                st.download_button(label="Click to Save File", data=log_text, file_name=file_name, mime="text/plain")
    
    else:
        #  password incorrect or not entered
        if "assigned_condition" not in st.session_state:
             st.session_state.assigned_condition = random.choice(["Condition A", "Condition B"])
        st.caption("Enter password to view controls.")

# =========================================================
# [MAIN INTERFACE]
# =========================================================

st.markdown("<div class='main-title'>🤖 AI Co-Writer Partner</div>", unsafe_allow_html=True)
st.markdown(f"""
<div class='welcome-box'>
    <p class='welcome-text'>Hello, {participant_id}! 👋</p>
    <p class='instruction-text'>I am your creative partner for this session.<br>Together, we will write a <span class='highlight'>Science-Fiction story</span> (approx. 500 words).</p>
    <hr style="margin: 20px 0;">
    <div style="text-align: left; display: inline-block; background-color: white; padding: 20px; border-radius: 10px;">
        <h4 style="margin-top: 0;">💡 How to collaborate:</h4>
        <ul style="margin-bottom: 0;">
            <li>Treat me as a fellow writer, not just a tool.</li>
            <li>Discuss ideas, characters, and settings with me freely.</li>
            <li>Our goal is a complete story with a <b>beginning, middle, and end.</b></li>
        </ul>
    </div>
</div>
""", unsafe_allow_html=True)

# Initialize Session State
if "thread_id" not in st.session_state:
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id
    st.session_state.messages = []

# Condition Check
current_asst_id = ASST_ID_A if st.session_state.assigned_condition == "Condition A" else ASST_ID_B

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User Input
if prompt := st.chat_input("Type your message here..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    client.beta.threads.messages.create(thread_id=st.session_state.thread_id, role="user", content=prompt)
    run = client.beta.threads.runs.create(thread_id=st.session_state.thread_id, assistant_id=current_asst_id)

    with st.spinner("AI Partner is thinking..."):
        while run.status != "completed":
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(thread_id=st.session_state.thread_id, run_id=run.id)
            if run.status in ["failed", "cancelled", "expired"]:
                st.error("Error occurred. Please refresh the page.")
                break

    if run.status == "completed":
        messages = client.beta.threads.messages.list(thread_id=st.session_state.thread_id)
        ai_response = messages.data[0].content[0].text.value
        st.session_state.messages.append({"role": "assistant", "content": ai_response})
        with st.chat_message("assistant"):
            st.markdown(ai_response)