import pandas as pd
from pathlib import Path
from fastmcp.server import FastMCP, Context
from typing import List, Dict, Any, Optional

# 전역 데이터 저장
DF: Optional[pd.DataFrame] = None

# MCP 서버 초기화
mcp = FastMCP(
    "MerchantSearchServer",
    instructions="""
    제주도 가맹점을 검색하는 서비스입니다.
    
    사용자가 가맹점명을 입력하면 search_merchant 함수를 사용하여 해당 가맹점의 상세 정보를 검색합니다.
    가맹점명은 부분 일치로 검색되며, 대소문자를 구분하지 않습니다.
    
    검색 결과에는 다음 정보가 포함됩니다:
    - 가맹점명, 업종, 주소, 개설일자
    - 이용건수구간, 이용금액구간
    - 현지인 이용 비중, 영업시간
    - 상세 정보
    """
)

# 데이터 로드 함수
def _load_df():
    global DF
    DF = pd.read_csv("./data/JEJU_MCT_DATA_modified.csv")
    return DF

# 서버 시작 시 데이터 로드
_load_df()

@mcp.tool()
def search_merchant(merchant_name: str) -> Dict[str, Any]:
    """
    가맹점명을 입력받아 해당 가맹점 정보를 검색합니다.
    
    매개변수:
      - merchant_name: 검색할 가맹점명 (부분 일치 지원)
    
    반환값:
      - 가맹점 정보가 담긴 딕셔너리
    """
    assert DF is not None, "DataFrame이 초기화되지 않았습니다."
    
    # 가맹점명으로 검색 (대소문자 구분 없음, 부분 일치)
    result = DF[(DF['기준연월'].astype(str) == '202308') & (DF['가맹점명'].astype(str) == merchant_name)]
    
    if len(result) == 0:
        return {
            "found": False,
            "message": f"'{merchant_name}'에 해당하는 가맹점을 찾을 수 없습니다.",
            "count": 0,
            "merchants": []
        }
    
    # 결과를 딕셔너리로 변환
    merchants = []
    for _, row in result.iterrows():
        merchant_info = {
            "가맹점명": row['가맹점명'],
            "업종": row['가맹점업종'],
            "주소": row['가맹점주소'],
            "개설일자": row['가맹점개설일자'],
            "이용건수구간": row['이용건수구간'],
            "이용금액구간": row['이용금액구간'],
            "현지인이용건수비중": row['현지인이용건수비중'],
            "영업시간": row['영업시간'],
            "상세정보": row['text']
        }
        merchants.append(merchant_info)

    #print(f"'{merchant_name}'에 해당하는 가맹점 {len(merchants)}개를 찾았습니다.")
    
    return {
        "found": True,
        "message": f"'{merchant_name}'에 해당하는 가맹점 {len(merchants)}개를 찾았습니다.",
        "count": len(merchants),
        "merchants": merchants
    }

if __name__ == "__main__":
    mcp.run()