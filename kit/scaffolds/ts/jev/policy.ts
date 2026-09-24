// Jev 결정 정책: 모델 버전, 임계값, 가중치를 이 모듈 한 곳에 둔다 (KIT/manual/03).
// 상태 태그: [잠정] 평가 전 가정 · [측정] 평가셋으로 튜닝함 (KIT/manual/04)
export const POLICY = {
  model: "jev-1.13.0",       // 버전 고정. jev-latest를 쓰지 않는다 (KIT/manual/05)
  topicMinConfidence: 0.75,  // [잠정] topic.confidence (Choice, 선택지 3개) · 선택지 수가 바뀌면 다시 튜닝
  refundYes: 0.7,            // [잠정] refund_requested.noul
  frustrationHigh: 1.5,      // [잠정] frustration.score (Score 0~2)
};
