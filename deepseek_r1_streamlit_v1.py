import streamlit as st
import requests
import json
from datetime import datetime
import subprocess

# Ollama 서버 설정
OLLAMA_HOST = "http://127.0.0.1:11434"

@st.cache_data(ttl=300)
def get_ollama_version():
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/version")
        return response.json().get('version', 'Unknown')
    except:
        return 'Not Available'

@st.cache_data(ttl=300)
def get_available_models():
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        if result.returncode == 0:
            models = []
            for line in result.stdout.splitlines()[1:]:  # 첫 줄 제외 (헤더)
                model_name = line.split()[0]  # 첫 번째 열 (모델 이름)
                models.append(model_name)
            return models
        else:
            return ["Error fetching models"]
    except Exception as e:
        return [f"Error: {str(e)}"]

# 스타일 추가 (채팅 색상)
st.markdown(
    """
    <style>
        .user-message {
            background-color: #007BFF;
            color: white;
            padding: 10px;
            border-radius: 10px;
            margin: 5px 0;
        }
        .assistant-message {
            background-color: #F1F1F1;
            color: black;
            padding: 10px;
            border-radius: 10px;
            margin: 5px 0;
        }
        .metrics-box {
            background-color: #222;
            color: white;
            padding: 10px;
            border-radius: 10px;
            margin-top: 10px;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# 시스템 정보 사이드바
with st.sidebar:
    st.header("⚙️ System Information")
    available_models = get_available_models()
    selected_model = st.selectbox("🧠 Select Model", available_models, index=0)
    ollama_ver = get_ollama_version()
    st.metric(label="🛠 Ollama Version", value=ollama_ver)
    st.divider()
    st.markdown(f"**📌 Current Model**: `{selected_model}`")
    st.caption(f"🕒 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "metrics" not in st.session_state:
    st.session_state.metrics = []
if "partial_response" not in st.session_state:
    st.session_state.partial_response = ""

# 채팅 인터페이스
st.title("🤖 SisaAI AI Chat")  
st.subheader("🚀 Smart AI Chat")

status_cols = st.columns(3)
with status_cols[0]:
    if st.button("🔄 Refresh Connection"):
        st.experimental_rerun()
with status_cols[1]:
    server_status = "✅ Online" if ollama_ver != 'Not Available' else "❌ Offline"
    st.markdown(f"**🖥️ Server Status**: {server_status}")
with status_cols[2]:
    st.metric("💬 Total Messages", len(st.session_state.messages))

# 채팅 기록 표시 (색상 적용)
for idx, message in enumerate(st.session_state.messages):
    if message["role"] == "user":
        st.markdown(f'<div class="user-message">{message["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="assistant-message">{message["content"]}</div>', unsafe_allow_html=True)
        if idx < len(st.session_state.metrics):
            with st.expander("📊 Technical Details"):
                st.json(st.session_state.metrics[idx])

# 사용자 입력 처리
if prompt := st.chat_input("Enter your message..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.markdown(f'<div class="user-message">{prompt}</div>', unsafe_allow_html=True)

    url = f"{OLLAMA_HOST}/api/chat"
    data = {
        "model": selected_model,
        "messages": st.session_state.messages,
        "stream": True
    }

    response_placeholder = st.empty()
    full_response = ""
    metrics = {}

    try:
        start_time = datetime.now()
        response = requests.post(url, json=data, stream=True)

        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line.decode('utf-8'))
                    if chunk.get("done"):
                        metrics = {
                            "response_time": f"{(datetime.now() - start_time).total_seconds():.2f}s",
                            "model": chunk.get('model', selected_model),
                            "created_at": chunk.get('created_at'),
                            "eval_count": chunk.get('eval_count'),
                            "eval_duration": chunk.get('eval_duration')
                        }
                    if chunk.get("message") and "content" in chunk["message"]:
                        full_response += chunk["message"]["content"]
                        response_placeholder.markdown(
                            f'<div class="assistant-message">{full_response}▌</div>',
                            unsafe_allow_html=True
                        )
            response_placeholder.markdown(f'<div class="assistant-message">{full_response}</div>', unsafe_allow_html=True)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            st.session_state.metrics.append(metrics)

            with st.expander("📊 시사AI Latest Response Metrics"):
                cols = st.columns(3)
                cols[0].metric("⏱️ Response Time", metrics.get('response_time', 'N/A'))
                cols[1].metric("🔢 Token Count", metrics.get('eval_count', 'N/A'))
                cols[2].metric("⚡ Processing Time", f"{metrics.get('eval_duration', 0)/1e9:.2f}s" if metrics.get('eval_duration') else 'N/A')

        else:
            st.error(f"🚨 API Error: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        st.error(f"🔌 Connection Error: {str(e)}")
        st.info("📢 Check if Ollama server is running with `ollama serve`")

# 사이드바에서 최신 Metrics 표시
with st.sidebar:
    st.divider()
    if st.session_state.metrics:
        latest_metrics = st.session_state.metrics[-1]
        st.markdown("📊 **Last Response Metrics**")
        st.markdown(
            f"""
            <div class="metrics-box">
            ⏱️ <b>Response Time:</b> {latest_metrics.get('response_time', 'N/A')}<br>
            🔢 <b>Tokens Generated:</b> {latest_metrics.get('eval_count', 'N/A')}<br>
            ⚡ <b>Processing Time:</b> {f"{latest_metrics.get('eval_duration', 0)/1e9:.2f}s" if latest_metrics.get('eval_duration') else 'N/A'}
            </div>
            """,
            unsafe_allow_html=True
        )
