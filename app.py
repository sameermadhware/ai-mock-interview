import streamlit as st
from litellm import completion
import os
import json
import uuid
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

st.set_page_config(page_title="AI vs AI System Design Interview", page_icon="🎙️", layout="wide")

st.title("🎙️ AI vs AI System Design Mock Interview Simulator")
st.markdown("Watch a fully automated, simulated technical interview between an AI Panel and an AI Candidate.")

def save_chat_history():
    if "session_id" in st.session_state:
        folder_path = os.path.join(os.getcwd(), 'sessions', st.session_state.session_id)
        os.makedirs(folder_path, exist_ok=True)
        file_path = os.path.join(folder_path, "chat_history.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(st.session_state.display_messages, f, indent=4)

def clear_simulation():
    st.session_state.display_messages = []
    st.session_state.is_running = False

# Sidebar Configuration
with st.sidebar:
    st.header("Setup Interview")
    problem_statement = st.text_area(
        "System Design Problem", 
        value="Design a URL Shortener like TinyURL",
        help="Enter the system design problem for the simulation.",
        on_change=clear_simulation
    )
    
    max_turns = st.slider("Max Speaker Interchanges", min_value=4, max_value=30, value=10, on_change=clear_simulation)
    
    st.markdown("---")
    st.markdown("**LLM Configuration**")
    
    AVAILABLE_MODELS = {
        "Gemini (gemini-2.5-flash)": "gemini/gemini-2.5-flash",
        "OpenAI (gpt-4o)": "openai/gpt-4o",
        "Claude (claude-3.5-sonnet)": "anthropic/claude-3-5-sonnet-20241022"
    }
    
    selected_model_display = st.selectbox(
        "Select Model Provider",
        options=list(AVAILABLE_MODELS.keys()),
        index=0,
        on_change=clear_simulation
    )
    model_name = AVAILABLE_MODELS[selected_model_display]
    
    start_button = st.button("Start Auto-Simulation", type="primary")

if start_button:
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.max_turns = max_turns
    st.session_state.model_name = model_name
    
    panelist_prompt = f"""You are simulating an end-to-end System Design Mock Interview panel for a Senior AI Architect/Consultant position.
The panel consists of two interviewers. You will interact with the candidate.
1. **Subha (TechLead)**: A very tech-driven interviewer who understands technology nuances, low-level details, data structures, specific algorithms, and micro-optimizations.
2. **Santosh (Architect)**: A high-level thinker who focuses on design failures, implementation challenges, scalability, system trade-offs, and overall platform architecture. This person has a tendency to put tricky scenarios and throw curve balls in between to gauge the candidate.

The topic of the interview is: "{problem_statement}"

CRITICAL INSTRUCTIONS FOR THE PANEL:
- The candidate MUST start by clarifying requirements. If they start designing immediately without clarifying constraints, you MUST politely interrupt and ask them to define functional and non-functional requirements.
- If the problem "{problem_statement}" involves Agentic AI or AI systems, you MUST explicitly ask the candidate to include an AI evaluation framework (e.g. LLM-as-a-judge, rogue metrics, human-in-the-loop, etc.) as part of the system design.
- When the interviewee shares engaging, robust design concepts, acknowledge them positively. Probe deeper into their choices naturally.
- You can decide whether Subha, Santosh, or both will respond based on the conversation.
- STRICTLY FORMAT your responses to include the speaker's name like this:
**Subha (TechLead)**: [Response text]
**Santosh (Architect)**: [Response text]
- NEVER generate the candidate's responses.
- To begin the interview, introduce yourselves briefly and present the problem statement to the candidate.
"""

    interviewee_prompt = f"""You are a Senior AI Architect/Consultant participating in a System Design Mock Interview.
The topic is: "{problem_statement}"

CRITICAL INSTRUCTIONS FOR YOU (THE CANDIDATE):
- The interview panel consists of Subha (TechLead) and Santosh (Architect).
- **YOUR EXPLICIT ROLE**: In the beginning, you MUST ask as many clarifying questions as possible before starting to design. Do not provide a system design immediately. Explicitly establish functional requirements, non-functional requirements, scale, and constraints.
- Only once the panelists answer your clarifications and agree on the scope, transition into the component design process.
- Your design explanations should sound engaging, highly professional, and insightful. Break down API design, database schema, algorithms, and bottlenecks.
- Speak in the first person directly to the panelists.
- Do NOT generate the panel's responses. You only speak for yourself.
"""

    st.session_state.panel_messages = [{"role": "system", "content": panelist_prompt}]
    st.session_state.interviewee_messages = [{"role": "system", "content": interviewee_prompt}]
    st.session_state.display_messages = []
    
    st.session_state.turn_count = 0
    st.session_state.current_speaker = "panel"
    st.session_state.is_running = True

# Display all existing visible messages
if "display_messages" in st.session_state:
    for msg in st.session_state.display_messages:
        avatar = "👥" if msg["role"] == "panel" else "👔"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

# Run the simulation loop
if st.session_state.get("is_running", False):
    if st.session_state.turn_count >= st.session_state.get("max_turns", 10):
        st.success("🏁 Simulation Reached Maximum Configured Turns.")
        st.session_state.is_running = False
    else:
        speaker = st.session_state.current_speaker
        avatar = "👥" if speaker == "panel" else "👔"
        
        with st.chat_message(speaker, avatar=avatar):
            message_placeholder = st.empty()
            full_response = ""
            
            max_retries = 3
            retry_count = 0
            success = False
            
            # Select the appropriate context history
            msgs = st.session_state.panel_messages if speaker == "panel" else st.session_state.interviewee_messages
            
            while retry_count < max_retries and not success:
                try:
                    response_stream = completion(
                        model=st.session_state.get("model_name", "gemini/gemini-2.5-flash"),
                        messages=msgs,
                        stream=True
                    )
                    
                    full_response = ""
                    for chunk in response_stream:
                        if chunk.choices[0].delta.content:
                            full_response += chunk.choices[0].delta.content
                            message_placeholder.markdown(full_response + "▌")
                    
                    message_placeholder.markdown(full_response)
                    success = True
                    
                except Exception as e:
                    error_msg = str(e)
                    if "503" in error_msg and retry_count < max_retries:
                        retry_count += 1
                        message_placeholder.warning(f"Received 503 error. Retrying in 10 seconds... (Attempt {retry_count}/{max_retries})")
                        time.sleep(10)
                        message_placeholder.empty()
                    else:
                        st.error(f"Error communicating with LLM: {error_msg}")
                        st.session_state.is_running = False
                        break
            
            if success:
                # Save to UI display log
                st.session_state.display_messages.append({"role": speaker, "content": full_response})
                save_chat_history()
                
                # Feed the response to both AI contexts
                if speaker == "panel":
                    # Panel remembers it as its own output
                    st.session_state.panel_messages.append({"role": "assistant", "content": full_response})
                    # Interviewee receives it as an input
                    st.session_state.interviewee_messages.append({"role": "user", "content": full_response})
                    st.session_state.current_speaker = "candidate"
                else:
                    # Candidate remembers it as its own output
                    st.session_state.interviewee_messages.append({"role": "assistant", "content": full_response})
                    # Panel receives it as an input
                    st.session_state.panel_messages.append({"role": "user", "content": full_response})
                    st.session_state.current_speaker = "panel"
                
                st.session_state.turn_count += 1
                
                # Small pause for UI UX
                time.sleep(1.5)
                
                # Trigger Streamlit to rerun and process the next turn
                st.rerun()