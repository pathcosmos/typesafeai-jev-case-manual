from typesafe_sdk import Choice, Noul, Score

QUESTIONS = {
    "topic": Choice(
        instructions={"question": "Which team should handle `ticket.message`?",
                      "focus": "Classify the customer's primary request."},
        criteria={
            "billing": {"what": "Charges, invoices, refunds", "not_for": "Order tracking"},
            "orders":  {"what": "Order status, delivery, returns", "not_for": "Charges"},
            "other":   "None of the above",                       # no-match 선택지
        },
    ),
    "refund_requested": Noul(                                     # 추측성 질문: billing 분기에서만 사용
        instructions="Does `ticket.message` explicitly request a refund or credit?",
    ),
    "frustration": Score(
        instructions="How frustrated does the customer appear in `ticket.message`?",
        criteria=["Calm and matter-of-fact", "Frustrated but civil", "Very angry or threatening to leave"],
    ),
}
