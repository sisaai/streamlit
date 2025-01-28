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
        # `ollama list` 명령어 실행
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        if result.returncode == 0:
            # 명령어 결과를 파싱하여 모델 이름 추출
            models = []
            for line in result.stdout.splitlines()[1:]:  # 첫 줄 제외 (헤더)
                model_name = line.split()[0]  # 첫 번째 열 (모델 이름)
                models.append(model_name)
            return models
        else:
            return ["Error fetching models"]
    except Exception as e:
        return [f"Error: {str(e)}"]

# 시스템 정보 사이드바
with st.sidebar:
    st.header("System Information")
    
    # Ollama에서 동적으로 모델 목록 불러오기
    available_models = get_available_models()
    
    # 모델 선택 드롭다운
    selected_model = st.selectbox(
        "Select Model",
        available_models,
        index=0  # 기본 선택 모델
    )
    
    ollama_ver = get_ollama_version()
    st.metric(label="Ollama Version", value=ollama_ver)
    st.divider()
    st.markdown(f"**Current Model**: `{selected_model}`")  # 선택된 모델 표시
    st.caption(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "metrics" not in st.session_state:
    st.session_state.metrics = []
if "partial_response" not in st.session_state:
    st.session_state.partial_response = ""

# 채팅 인터페이스
st.title("🚀 Ollama Chat Interface")
st.subheader("Advanced Monitoring Version")

# 연결 상태 표시기
status_cols = st.columns(3)
with status_cols[0]:
    st.button("🔄 Refresh Connection")
with status_cols[1]:
    server_status = "✅ Online" if ollama_ver != 'Not Available' else "❌ Offline"
    st.markdown(f"**Server Status**: {server_status}")
with status_cols[2]:
    st.metric("Total Messages", len(st.session_state.messages))

# 채팅 기록 표시
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant" and idx < len(st.session_state.metrics):
            with st.expander("Technical Details"):
                st.json(st.session_state.metrics[idx])

# 사용자 입력 처리
if prompt := st.chat_input("Enter your message..."):
    # 사용자 메시지 처리
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Ollama API 요청 (선택된 모델 사용)
    url = f"{OLLAMA_HOST}/api/chat"
    data = {
        "model": selected_model,  # 선택된 모델 사용
        "messages": st.session_state.messages,
        "stream": True
    }

    with st.chat_message("assistant"):
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
                            response_placeholder.markdown(full_response + "▌")
                
                response_placeholder.markdown(full_response)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_response
                })
                st.session_state.metrics.append(metrics)
                
                with st.expander("Latest Response Metrics"):
                    cols = st.columns(3)
                    cols[0].metric("Response Time", metrics.get('response_time', 'N/A'))
                    cols[1].metric("Token Count", metrics.get('eval_count', 'N/A'))
                    cols[2].metric("Processing Time", 
                                 f"{metrics.get('eval_duration', 0)/1e9:.2f}s" if metrics.get('eval_duration') else 'N/A')
                    
            else:
                st.error(f"API Error: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            st.error(f"Connection Error: {str(e)}")
            st.info("Check if Ollama server is running with `ollama serve`")

# 사이드바 하단에 추가 정보 표시
with st.sidebar:
    st.divider()
    if st.session_state.metrics:
        latest_metrics = st.session_state.metrics[-1]
        st.markdown("**Last Response Metrics**")
        st.write(f"⏱️ Response Time: {latest_metrics.get('response_time', 'N/A')}")
        st.write(f"🔢 Tokens Generated: {latest_metrics.get('eval_count', 'N/A')}")

