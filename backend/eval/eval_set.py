"""
Evaluation set: 29 questions spanning every document topic, each with the document
that should be retrieved and keywords a correct answer should contain. Facts were
cross-checked against the actual docs/ text (grep'd, not recalled from memory)
before being written here, so a failure means the pipeline is wrong, not the eval
data.

expected_keywords are matched case-insensitively as substrings of the generated
answer - deliberately simple (not semantic similarity) so a failure is easy to
read directly off the eval report.
"""

from dataclasses import dataclass


@dataclass
class EvalCase:
    question: str
    expected_document: str
    expected_keywords: list[str]


EVAL_SET: list[EvalCase] = [
    EvalCase(
        "What VAT rate applies to imports into South Africa?",
        "Customs and VAT Compliance Guide",
        ["15%"],
    ),
    EvalCase(
        "Why do I need the correct HS code on a shipment?",
        "Customs and VAT Compliance Guide",
        ["HS code", "duty"],
    ),
    EvalCase(
        "Under FOB terms, who is responsible for the goods?",
        "Incoterms Explainer — FOB, CIF, EXW, DAP",
        ["FOB"],
    ),
    EvalCase(
        "Who arranges transport under DAP terms?",
        "Incoterms Explainer — FOB, CIF, EXW, DAP",
        ["seller"],
    ),
    EvalCase(
        "What rebate do I get if my delivery is 2 business days late?",
        "Delivery SLA Policy — General Terms and Penalties",
        ["25%"],
    ),
    EvalCase(
        "How long does delivery take from Johannesburg to Durban?",
        "Delivery SLA — Domestic South African Routes",
        ["1 business day"],
    ),
    EvalCase(
        "What is the guaranteed transit time from Johannesburg to Harare?",
        "Delivery SLA — Zimbabwe Corridor",
        ["3 business days"],
    ),
    EvalCase(
        "What border post is used for Gaborone-bound shipments?",
        "Delivery SLA — Botswana Corridor",
        ["Skilpadshek", "Pioneer Gate"],
    ),
    EvalCase(
        "How long does delivery take from Johannesburg to Beira?",
        "Delivery SLA — Mozambique Corridor",
        ["5 business days"],
    ),
    EvalCase(
        "How long do I have to report damaged goods?",
        "Damaged Goods Claims Process",
        ["48 hours", "5 business days"],
    ),
    EvalCase(
        "When is a shipment considered lost?",
        "Lost Goods Claims Process",
        ["10 business days"],
    ),
    EvalCase(
        "What's the difference between carrier liability and cargo insurance?",
        "Cargo Insurance and Carrier Liability",
        ["liability", "insurance"],
    ),
    EvalCase(
        "Do I need a Safety Data Sheet to ship dangerous goods?",
        "Dangerous Goods Handling Policy — Overview",
        ["Safety Data Sheet", "SDS"],
    ),
    EvalCase(
        "How is the packing group determined for a flammable liquid?",
        "Dangerous Goods — Class 3: Flammable Liquids",
        ["flash point"],
    ),
    EvalCase(
        "How fast does a corrosive substance need to destroy skin tissue to be Packing Group I?",
        "Dangerous Goods — Class 8: Corrosive Substances",
        ["60 minutes"],
    ),
    EvalCase(
        "Can lithium batteries be shipped?",
        "Dangerous Goods — Class 9: Miscellaneous Dangerous Goods",
        ["watt-hour", "lithium"],
    ),
    EvalCase(
        "What is a SADC Certificate of Origin used for?",
        "Cross-Border Documentation Checklist — Overview",
        ["SADC", "duty"],
    ),
    EvalCase(
        "Which authority handles customs clearance into Zimbabwe?",
        "Cross-Border Documentation Checklist — Zimbabwe",
        ["ZIMRA"],
    ),
    EvalCase(
        "Which authority handles customs clearance into Botswana?",
        "Cross-Border Documentation Checklist — Botswana",
        ["BURS"],
    ),
    EvalCase(
        "What is a one-stop border post on the Zambia corridor?",
        "Cross-Border Documentation Checklist — Zambia",
        ["Chirundu"],
    ),
    EvalCase(
        "Why do invoices for Mozambique shipments need to be bilingual?",
        "Cross-Border Documentation Checklist — Mozambique",
        ["Portuguese", "bilingual"],
    ),
    EvalCase(
        "How often is the fuel surcharge reviewed?",
        "Fuel Surcharge Policy",
        ["month", "1st"],
    ),
    EvalCase(
        "How is volumetric weight calculated?",
        "General Pricing Policy",
        ["6000"],
    ),
    EvalCase(
        "How many hours can a driver drive without a break?",
        "Driver Hours of Service Policy",
        ["5 continuous hours"],
    ),
    EvalCase(
        "What is Baobab's policy on alcohol use by drivers?",
        "Driver Safety and Compliance Policy",
        ["zero-tolerance", "breathalyser"],
    ),
    EvalCase(
        "What is checked during a pre-trip vehicle inspection?",
        "Vehicle Inspection Checklist",
        ["tyre", "brake"],
    ),
    EvalCase(
        "Why does the chatbot log my questions?",
        "POPIA Data Privacy Notice",
        ["rate limit", "IP address"],
    ),
    EvalCase(
        "How do I track my shipment?",
        "General FAQ — Tracking and Delivery",
        ["client portal", "waybill"],
    ),
    EvalCase(
        "What payment terms are available for account clients?",
        "General FAQ — Payment Terms",
        ["30-day"],
    ),
]
