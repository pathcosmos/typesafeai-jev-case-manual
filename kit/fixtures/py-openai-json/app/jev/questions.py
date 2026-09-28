from typesafe_sdk import Choice, Noul

QUESTIONS = {
    "department_choice": Choice(
        instructions="다음 고객 문의를 가장 관련 있는 부서로 분류하세요. 결정의 기준은 문의의 주요 내용입니다.\n\n문의: `message`",
        criteria={
            "billing": "요금, 환불, 결제 문제, 돈 관련 요청",
            "shipping": "배송 상태, 지연, 배송지 변경, 배송 추적",
            "account": "계정 관련, 비밀번호, 프로필, 기타",
        },
    ),
    "urgent_noul": Noul(
        instructions="이 고객 문의가 즉시 처리해야 할 긴급 상황을 나타내는가? 기준은 고객의 현재 손실, 서비스 중단, 안전 문제입니다.\n\n문의: `message`",
        criteria={
            "true": "긴급함: 돈 손실, 서비스 이용 불가, 안전",
            "false": "일반적: 향후 예방, 정보 요청, 기능 제안",
        },
    ),
}
