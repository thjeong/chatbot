import os, json, asyncio
import google.generativeai as genai
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
import proto  # pip로 따로 설치不要 (google-generativeai가 끌어옵니다)

async def main():
    # 1) Gemini 준비(도구 정의는 최소 1개만 하드코딩)
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
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

    # 2) MCP 서버 연결(환경에 맞게 명령 수정)
    # transport, client = await stdio_client("uv", ["run","mcp_server.py"])
    async with stdio_client(server_params) as (read, write):
        # ✅ 2) 스트림으로 ClientSession을 만들고
        async with ClientSession(read, write) as session:
            # ✅ 3) 세션을 initialize 한다
            await session.initialize()

            # 3) 유저 한 마디 → Gemini 응답에서 function_call 1개만 처리
            resp = chat.send_message("휴일로 어때?")  # 예시 입력
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
                print(final.text)
            else:
                # 함수 호출 없으면 일반 답변
                print(resp.text)

    #await transport.close()

if __name__ == "__main__":
    asyncio.run(main())
