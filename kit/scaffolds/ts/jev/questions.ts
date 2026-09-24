import { choice, noul, score } from "@typesafe-ai/sdk";

export const QUESTIONS = {
  topic: choice(
    { question: "Which team should handle `ticket.message`?", focus: "Classify the customer's primary request." },
    { billing: "Charges, invoices, refunds", orders: "Order status, delivery, returns", other: "None of the above" },
  ),
  refund_requested: noul("Does `ticket.message` explicitly request a refund or credit?"),
  frustration: score("How frustrated does the customer appear in `ticket.message`?",
    ["Calm and matter-of-fact", "Frustrated but civil", "Very angry or threatening to leave"]),
};
