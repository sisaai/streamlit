import streamlit as st
import requests
import json
from datetime import datetime

# Ollama 서버 설정
OLLAMA_HOST = "http://127.0.0.1:11434"
MODEL_NAME = "sisaai/sisaai-llama3.1:latest"

@st.cache_data(ttl=300)
def get_ollama_version():
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/version")
        return response.json().get('version', 'Unknown')
    except:
        return 'Not Available'

# 시스템 정보 사이드바
with st.sidebar:
    st.header("System Information")
    ollama_ver = get_ollama_version()
    st.metric(label="Ollama Version", value=ollama_ver)
    st.divider()
    st.markdown(f"**Current Model**: `{MODEL_NAME}`")
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
    
    # Ollama API 요청 (스트리밍 활성화)
    url = f"{OLLAMA_HOST}/api/chat"
    data = {
        "model": MODEL_NAME,
        "messages": st.session_state.messages,
        "stream": True  # 스트리밍 활성화
    }

    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        metrics = {}
        
        try:
            start_time = datetime.now()
            response = requests.post(url, json=data, stream=True)
            
            if response.status_code == 200:
                # 스트리밍 응답 처리
                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line.decode('utf-8'))
                        
                        # 메트릭 정보 수집 (마지막 청크에서만)
                        if chunk.get("done"):
                            metrics = {
                                "response_time": f"{(datetime.now() - start_time).total_seconds():.2f}s",
                                "model": chunk.get('model', MODEL_NAME),
                                "created_at": chunk.get('created_at'),
                                "eval_count": chunk.get('eval_count'),
                                "eval_duration": chunk.get('eval_duration')
                            }
                        
                        # 응답 내용 누적
                        if chunk.get("message") and "content" in chunk["message"]:
                            full_response += chunk["message"]["content"]
                            response_placeholder.markdown(full_response + "▌")
                
                # 최종 응답 업데이트
                response_placeholder.markdown(full_response)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_response
                })
                st.session_state.metrics.append(metrics)
                
                # 실시간 메트릭 표시
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
