import streamlit as st
from openai import OpenAI
import random
import time
import json

# [SECURITY] OpenAI API Key
if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    st.error("🚨 Error: OPENAI_API_KEY not found in Secrets.")
    st.stop()

# [MODEL SETTING] - 2024-04-09 snapshot version of gpt-4-turbo, which is the most recent version as of June 2024.
client = OpenAI(api_key=api_key)
MODEL_VERSION = "gpt-4-turbo-2024-04-09"

st.set_page_config(page_title="Sci-Fi Writing Experiment", page_icon="🧪", layout="wide")

# =========================================================
# [JAVASCRIPT TIMER] countdown time display 
# =========================================================
def show_timer(minutes, message="Time Remaining"):
    seconds = minutes * 60
    timer_html = f"""
        <div style="
            position: fixed; top: 60px; right: 20px; 
            background-color: #fff0f6; border: 2px solid #d63384; 
            padding: 10px 20px; border-radius: 10px; 
            font-size: 1.2rem; font-weight: bold; color: #d63384; 
            z-index: 9999; box-shadow: 0px 4px 6px rgba(0,0,0,0.1);">
            ⏳ {message}: <span id="time">Loading...</span>
        </div>
        <script>
        function startTimer(duration, display) {{
            var timer = duration, minutes, seconds;
            var interval = setInterval(function () {{
                minutes = parseInt(timer / 60, 10);
                seconds = parseInt(timer % 60, 10);

                minutes = minutes < 10 ? "0" + minutes : minutes;
                seconds = seconds < 10 ? "0" + seconds : seconds;

                display.textContent = minutes + ":" + seconds;

                if (--timer < 0) {{
                    clearInterval(interval);
                    display.textContent = "00:00";
                    alert("Time is up! Please ask the researcher for next steps.");
                }}
            }}, 1000);
        }}
        window.onload = function () {{
            var duration = {seconds};
            var display = document.querySelector('#time');
            startTimer(duration, display);
        }};
        </script>
    """
    st.components.v1.html(timer_html, height=0)

# [CSS STYLING]
st.markdown("""
    <style>
    .main-title { font-size: 2.2rem; font-weight: 700; text-align: center; color: #1E1E1E; margin-bottom: 10px; }
    .phase-header { font-size: 1.5rem; font-weight: 600; color: #0068C9; margin-bottom: 20px; text-align: center; border-bottom: 2px solid #eee; padding-bottom: 10px; }
    .instruction-box { background-color: #f8f9fa; padding: 25px; border-radius: 10px; border: 1px solid #ddd; margin-bottom: 20px; line-height: 1.6; }
    .stTextArea textarea { font-size: 1.1rem !important; line-height: 1.6 !important; font-family: 'Arial', sans-serif !important; height: 500px !important; }
    </style>
""", unsafe_allow_html=True)

# [SESSION STATE INITIALIZATION]
if "participant_id" not in st.session_state: st.session_state.participant_id = None
if "assigned_group" not in st.session_state: st.session_state.assigned_group = None
if "current_phase" not in st.session_state: st.session_state.current_phase = "Login"
if "messages" not in st.session_state: st.session_state.messages = []
if "story_content" not in st.session_state: st.session_state.story_content = ""

# =========================================================
# [CONTENT SETTINGS] - System Prompts & User Guides
# =========================================================

# 1. AI System Prompts (Hidden from User)
SYS_PROMPT_STRATEGIC = """
You are a Generative AI partner for a creative writing brainstorming session.
Today, the user will be writing a short Sci-Fi story.
You must strictly follow the "Discourse Engineering" guidelines:
1. Construction: Do not just accept ideas. Ask thoughtful questions.
2. Co-construction: Combine user ideas with yours. Aim for shared conclusions.
3. Conflict: Question assumptions. Engage in critical dialogue.
"""

SYS_PROMPT_BASELINE = """
You are a helpful, friendly AI writing assistant.
Your goal is to help the user brainstorm a Sci-Fi story.
Guidelines:
1. Be Supportive & Natural.
2. Be Reactive: Answer questions clearly. Do not proactively lead or critique unless asked.
3. Follow the User: Assist, do not teach.
"""

# 2. Human Guidelines (Phase 0) - Blind to Condition Names
# "Instruction A" / "Instruction B" 
GUIDE_INSTRUCTED = """
<h3 style='color:#333;'>🎯 Guidelines for Brainstorming</h3>
<p>To get the best results, try using the following strategies when chatting with the AI:</p>
<ul>
    <li><b>Dig Deeper:</b> Don't just accept the first answer. Ask follow-up questions.</li>
    <li><b>Collaborate:</b> Combine the AI's ideas with your own. Treat it as a partnership.</li>
    <li><b>Challenge:</b> Don't be afraid to disagree. Challenge assumptions to fix logical holes.</li>
</ul>
"""

GUIDE_NEUTRAL = """
<h3 style='color:#333;'>🎯 Guidelines for Brainstorming</h3>
<p>You will brainstorm a Sci-Fi story with an AI partner.</p>
<ul>
    <li>Chat naturally as you would with a human partner.</li>
    <li>Discuss characters, settings, and plots together.</li>
    <li>Feel free to ask for ideas or feedback anytime.</li>
</ul>
"""

# [GROUP DEFINITION] 
# type: 연구자만 보는 라벨
GROUPS = {
    "G1": {"type": "Instructed_Strategic", "guide": GUIDE_INSTRUCTED, "sys_prompt": SYS_PROMPT_STRATEGIC},
    "G2": {"type": "Instructed_Baseline", "guide": GUIDE_INSTRUCTED, "sys_prompt": SYS_PROMPT_BASELINE},
    "G3": {"type": "Neutral_Strategic",    "guide": GUIDE_NEUTRAL,    "sys_prompt": SYS_PROMPT_STRATEGIC},
    "G4": {"type": "Neutral_Baseline",     "guide": GUIDE_NEUTRAL,    "sys_prompt": SYS_PROMPT_BASELINE},
}

# =========================================================
# [SIDEBAR] ADMIN PANEL (Researcher Only)
# =========================================================
with st.sidebar:
    st.title("🛡️ Researcher Admin")
    st.info("Pass: 1234") 
    admin_pass = st.text_input("Admin Password", type="password")

    if admin_pass == "1234":
        st.success("Unlocked")
        
        st.markdown("---")
        st.markdown("### 📊 Status Monitor")
        # monitoring session by researcher 
        if st.session_state.participant_id:
            st.write(f"**Participant:** {st.session_state.participant_id}")
            # group information only visible to researcher 
            grp = st.session_state.assigned_group
            st.write(f"**Group:** {grp} ({GROUPS[grp]['type']})")
            st.write(f"**Phase:** {st.session_state.current_phase}")
        else:
            st.warning("No participant logged in.")

        st.markdown("---")
        st.markdown("### 🕹️ Controls")
        
        # [PHASE CONTROL] 강제 이동
        phase_options = ["Login", "Phase 0: Instruction", "Phase 1: Brainstorming", "Phase 2: Writing", "Submission"]
        try: idx = phase_options.index(st.session_state.current_phase)
        except: idx = 0
        new_phase = st.selectbox("Force Phase Jump:", phase_options, index=idx)
        if st.button("Go to Phase"):
            st.session_state.current_phase = new_phase
            st.rerun()
            
        st.markdown("---")
        st.markdown("### 💾 Data Management")
        
        # [DOWNLOAD LOG] researcher only
        if st.session_state.participant_id:
            log_data = {
                "participant_id": st.session_state.participant_id,
                "assigned_group": st.session_state.assigned_group,
                "condition_detail": GROUPS[st.session_state.assigned_group]['type'],
                "final_story": st.session_state.story_content,
                "chat_history": st.session_state.messages
            }
            json_str = json.dumps(log_data, indent=2, ensure_ascii=False)
            file_name = f"LOG_{st.session_state.participant_id}_{st.session_state.assigned_group}.json"
            
            st.download_button(
                label="📥 Download Log JSON",
                data=json_str,
                file_name=file_name,
                mime="application/json",
                type="primary"
            )
        else:
            st.caption("No data to download yet.")

        st.markdown("---")
        # [RESET]
        if st.button("⚠️ RESET FOR NEXT PARTICIPANT", type="primary"):
            st.session_state.clear() # all session state clear
            st.rerun()

# =========================================================
# [MAIN FLOW]
# =========================================================

# --- STEP 1: LOGIN (participant) ---
if st.session_state.current_phase == "Login":
    st.markdown("<div class='main-title'>🧪 Sci-Fi Co-Writing Experiment</div>", unsafe_allow_html=True)
    st.info("Welcome. Please enter your ID to begin.")
    
    with st.form("login_form"):
        p_id = st.text_input("Participant ID (e.g., P01):")
        submitted = st.form_submit_button("Start Experiment")
        
        if submitted and p_id:
            st.session_state.participant_id = p_id
            # [RANDOM ASSIGNMENT] 4개 중 하나 랜덤 배정 (여기서 확정됨)
            st.session_state.assigned_group = random.choice(list(GROUPS.keys()))
            st.session_state.current_phase = "Phase 0: Instruction"
            st.rerun()

# --- STEP 2: INSTRUCTION (5 Min) ---
elif st.session_state.current_phase == "Phase 0: Instruction":
    show_timer(5, "Reading Time")
    
    st.markdown(f"<div class='phase-header'>Step 1: Guidelines (5 min)</div>", unsafe_allow_html=True)
    
    # assigned group guideline(blind to condition names)
    group_settings = GROUPS[st.session_state.assigned_group]
    st.markdown(f"<div class='instruction-box'>{group_settings['guide']}</div>", unsafe_allow_html=True)
    
    st.write("")
    st.info("Please read the instructions carefully. Click below when ready.")
    
    if st.button("Start Brainstorming (Go to Step 2) 👉"):
        st.session_state.current_phase = "Phase 1: Brainstorming"
        st.rerun()

# --- STEP 3: BRAINSTORMING (15 Min) ---
elif st.session_state.current_phase == "Phase 1: Brainstorming":
    show_timer(15, "Brainstorming")
    
    st.markdown(f"<div class='phase-header'>Step 2: Brainstorming with AI (15 min)</div>", unsafe_allow_html=True)
    
    group_settings = GROUPS[st.session_state.assigned_group]
    
    # Chat UI
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Brainstorm ideas here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        # Chat Completions API Call (System Prompt Injection)
        messages_payload = [{"role": "system", "content": group_settings["sys_prompt"]}] + st.session_state.messages
        
        with st.spinner("AI is thinking..."):
            try:
                response = client.chat.completions.create(
                    model=MODEL_VERSION,
                    messages=messages_payload,
                    temperature=0.7,
                    max_tokens=400
                )
                ai_msg = response.choices[0].message.content
                st.session_state.messages.append({"role": "assistant", "content": ai_msg})
                with st.chat_message("assistant"): st.markdown(ai_msg)
            except Exception as e:
                st.error(f"API Error: {e}")

    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col3:
        if st.button("Finish Brainstorming & Start Writing 👉", type="primary"):
            st.session_state.current_phase = "Phase 2: Writing"
            st.rerun()

# --- STEP 4: WRITING (25 Min) ---
elif st.session_state.current_phase == "Phase 2: Writing":
    show_timer(25, "Writing Time")
    
    st.markdown(f"<div class='phase-header'>Step 3: Writing Story (25 min)</div>", unsafe_allow_html=True)
    
    col_left, col_right = st.columns([1, 1], gap="large")
    
    with col_left:
        st.info("💬 Chat History (Review Only)")
        with st.container(height=600):
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
    
    with col_right:
        st.warning("📝 Write your 500-word Sci-Fi Story")
        story_input = st.text_area("Start writing here...", value=st.session_state.story_content, height=500)
        st.session_state.story_content = story_input
        st.caption(f"Word Count: {len(story_input.split())}")
        
        st.markdown("---")
        if st.button("✅ Submit Story", type="primary", use_container_width=True):
            st.session_state.current_phase = "Submission"
            st.rerun()

# --- STEP 5: SUBMISSION (Survey Link) ---
elif st.session_state.current_phase == "Submission":
    st.markdown("<div class='main-title'>🎉 Experiment Completed!</div>", unsafe_allow_html=True)
    st.success("Your story has been submitted.")
    
    # [FIXED] 박사님의 진짜 퀄트릭스 링크 적용
    qualtrics_base_url = "https://iu.co1.qualtrics.com/jfe/form/SV_0iJ9n921PlFCxNQ"
    
    # URL 뒤에 꼬리표(PID, GROUP) 붙이기
    # 결과 예시: .../SV_0iJ9n921PlFCxNQ?PID=P01&GROUP=G1
    final_link = f"{qualtrics_base_url}?PID={st.session_state.participant_id}&GROUP={st.session_state.assigned_group}"
    
    st.markdown(f"""
        <div style="background-color:#e8f4fd; padding:30px; border-radius:10px; text-align:center; margin-top:20px;">
            <h3>👇 Final Step</h3>
            <p style="font-size:1.1rem;">Please click the link below to complete the post-experiment survey.</p>
            <br>
            <a href="{final_link}" target="_blank" style="
                background-color: #0068C9; color: white; padding: 18px 30px; 
                text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 1.3rem; 
                box-shadow: 0px 4px 6px rgba(0,0,0,0.1);">
                Go to Post-Survey 🔗
            </a>
            <br><br>
        </div>
    """, unsafe_allow_html=True)
    
    st.warning("Please notify the researcher that you have finished.")