"""
Evaluation set: 29 single-document questions spanning every document topic, plus
cases that stress two behaviors the single-doc cases can't reach - the low-confidence
"not found" fallback (step 12) and retrieval across a question that legitimately spans
two documents. Facts were cross-checked against the actual docs/ text (grep'd, not
recalled from memory) before being written here, so a failure means the pipeline is
wrong, not the eval data.

expected_keywords are matched case-insensitively as substrings of the generated
answer - deliberately simple (not semantic similarity) so a failure is easy to
read directly off the eval report. A single keyword entry may list interchangeable
phrasings separated by '|' (e.g. "BURS|Botswana Unified Revenue Service") when the
source docs themselves use both forms - either one is a correct answer.

expected_documents (plural) is for cases where a correct answer requires chunks from
more than one document - scored as "every listed document appears somewhere in the
top-k", not "the top result matches".

expects_not_found marks cases where the correct behavior is the low-confidence
fallback, not an answer - scored by checking the RAG chain returned no sources rather
than by keyword matching.
"""

from dataclasses import dataclass, field


@dataclass
class EvalCase:
    question: str
    expected_document: str | None = None
    expected_keywords: list[str] = field(default_factory=list)
    expected_documents: list[str] | None = None
    expects_not_found: bool = False


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
        ["BURS|Botswana Unified Revenue Service"],
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

    # --- Multi-document cases: a correct answer needs chunks from more than one doc ---
    EvalCase(
        "What documents do I need and how long will delivery take to Lusaka, Zambia?",
        expected_documents=[
            "Cross-Border Documentation Checklist — Zambia",
            "Delivery SLA — Zambia Corridor",
        ],
    ),
    EvalCase(
        "What border post do I use and what's the guaranteed transit time to Gaborone?",
        expected_documents=[
            "Cross-Border Documentation Checklist — Botswana",
            "Delivery SLA — Botswana Corridor",
        ],
    ),

    # --- Not-found cases: the correct behavior is the low-confidence fallback, not a guess ---
    EvalCase(
        # Adversarial: in-domain freight vocabulary, plausible question, but the
        # corpus only covers road freight - stresses the confidence threshold
        # directly rather than an obviously off-topic question would.
        "Do you offer air freight services for urgent shipments?",
        expects_not_found=True,
    ),
    EvalCase(
        "What are your rail freight rates to Cape Town?",
        expects_not_found=True,
    ),
    EvalCase(
        "What's a good recipe for koeksisters?",
        expects_not_found=True,
    ),
]
