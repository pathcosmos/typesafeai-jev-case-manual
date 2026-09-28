# Jev 결정 정책: 모델 버전, 임계값을 이 모듈 한 곳에 둔다.
# 상태 태그: [잠정] 평가 전 가정

MODEL = "jev-1.13.0"

DEPARTMENT_CONFIDENCE_GATE = 0.3  # [잠정] department_choice.confidence · confidence < 0.3이면 사람 검토
URGENT_THRESHOLD = 0.6             # [잠정] urgent_noul.noul >= 0.6이면 긴급
RUNNER_UP_PROB = 0.15              # [잠정] 2순위 팀 알림 확률 임계값
