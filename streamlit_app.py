import streamlit as st
import os, json, asyncio
import google.generativeai as genai
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
import proto  # pip로 따로 설치不要 (google-generativeai가 끌어옵니다)

# import shutil
# os.makedirs("/root/.streamlit", exist_ok=True)
# shutil.copy("secrets.toml", "/root/.streamlit/secrets.toml")

GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
google_api_key = GOOGLE_API_KEY  # langchain에서 사용할 변수명

genai.configure(api_key=GOOGLE_API_KEY)

# Gemini 모델 선택
model = genai.GenerativeModel("gemini-2.5-flash")

# Streamlit App UI

st.set_page_config(page_title="2025년 빅콘테스트 AI데이터 활용분야 - 맛집을 수호하는 AI비밀상담사")

# Replicate Credentials
with st.sidebar:
    st.title("맛집을 수호하는 AI비밀상담사")

st.title("🔑 신한 소상공인 비밀상담소")
st.subheader("머리아픈 🍀 마케팅 어떻게 하면 좋을까?")

st.write("")

st.write("#우리동네 #숨은맛집 #소상공인 #마케팅 #전략 .. 🤤")

st.write("")

# image_path = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRTHBMuNn2EZw3PzOHnLjDg_psyp-egZXcclWbiASta57PBiKwzpW5itBNms9VFU8UwEMQ&usqp=CAU"
# image_html = f"""
# <div style="display: flex; justify-content: center;">
#     <img src="{image_path}" alt="centered image" width="50%">
# </div>
# """
# st.markdown(image_html, unsafe_allow_html=True)

st.write("")

greeting = "어떤 가게를 어떻게 도와줄까요?"

# Store LLM generated responses
if "messages" not in st.session_state.keys():
    st.session_state.messages = [{"role": "assistant", "content": greeting}]

# Display or clear chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

def clear_chat_history():
    st.session_state.messages = [{"role": "assistant", "content": greeting}]

st.sidebar.button('Clear Chat History', on_click=clear_chat_history)

def render_chat_message(role: str, content: str):
    with st.chat_message(role):
        st.markdown(content)

genai.configure(api_key=GOOGLE_API_KEY)
tools = [{
    "function_declarations": [{
        "name": "search_merchant",
        "description": "가맹점명을 입력받아 해당 가맹점 정보를 검색합니다",
        "parameters": {
            "type": "object",
            "properties": {"merchant_name": {"type":"string"}},
            "required": ["merchant_name"]
        }
    }]
}]
model = genai.GenerativeModel("gemini-2.5-pro", tools=tools)
chat = model.start_chat()

server_params = StdioServerParameters(
    command="uv",
    args=["run","mcp_server.py"],
    env=None
)   

async def process_user_input(prompt):
    """사용자 입력을 처리하는 async 함수"""
    # 2) MCP 서버 연결(환경에 맞게 명령 수정)
    # transport, client = await stdio_client("uv", ["run","mcp_server.py"])
    async with stdio_client(server_params) as (read, write):
        # ✅ 2) 스트림으로 ClientSession을 만들고
        async with ClientSession(read, write) as session:
            # ✅ 3) 세션을 initialize 한다
            await session.initialize()

            # 3) 유저 한 마디 → Gemini 응답에서 function_call 1개만 처리
            resp = chat.send_message(prompt)  # 예시 입력
            fc = None
            if resp.candidates and resp.candidates[0].content.parts:
                for p in resp.candidates[0].content.parts:
                    if getattr(p, "function_call", None):
                        fc = p.function_call
                        break

            if fc:
                # 4) MCP tool 실행
                name = fc.name
                args: dict = proto.Message.to_dict(fc).get("args", {})
                #args = fc.args if isinstance(fc.args, dict) else json.loads(fc.args)
                mcp_result = await session.call_tool(name, args)

                # 5) 결과를 function_response로 되돌려주기(텍스트만 단순 추출)
                text_out = ""
                for c in getattr(mcp_result, "content", []) or []:
                    if (isinstance(c, dict) and c.get("type")=="text"):
                        text_out += c.get("text","")
                    elif getattr(c, "type", None) == "text":
                        text_out += getattr(c, "text", "")

                final = chat.send_message([{
                    "function_response": {"name": name, "response": {"ok": True, "text": text_out}}
                }])
                return final.text
            else:
                # 함수 호출 없으면 일반 답변
                return resp.text

# User-provided prompt
if prompt := st.chat_input("질문을 입력하세요"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    render_chat_message("user", prompt)

    with st.spinner("Thinking..."):
        try:
            reply = asyncio.run(process_user_input(prompt))
            st.session_state.messages.append({"role": "assistant", "content": reply})
            render_chat_message("assistant", reply)
        except Exception as e:
            error_msg = f"오류가 발생했습니다: {str(e)}"
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
            render_chat_message("assistant", error_msg)
