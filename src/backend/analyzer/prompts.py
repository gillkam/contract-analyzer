
COMPLIANCE_QUESTIONS = [
    "Password Management",
    "IT Asset Management",
    "Security Training & Background Checks",
    "Data in Transit Encryption",
    "Network Authentication & Authorization Protocols",
]

# Detailed requirements for each question — numbered sub-requirements for precise scoring
COMPLIANCE_REQUIREMENTS = {
    "Password Management": (
        "Check EACH sub-requirement below against the contract. Mark YES only if there is explicit evidence.\n"
        "Sub-requirements (7 total):\n"
        "  1. Password length/strength standards documented\n"
        "  2. Prohibition of default and known-compromised passwords\n"
        "  3. Secure storage — no plaintext; salted hashing if stored\n"
        "  4. Brute-force protections — account lockout or rate limiting\n"
        "  5. Prohibition on password sharing\n"
        "  6. Vaulting of privileged credentials and recovery codes\n"
        "  7. Time-based rotation for break-glass credentials\n"
        "HINT: Password strength/length may appear in Section 6.6(a); compromised-password screening in 6.6(b); "
        "storage in 6.6(c); lockout in 6.6(d); sharing in 6.6(e); vaulting in 6.6(f)/PASS-03; rotation in PASS-04.\n"
        "confidence = (number of YES / 7) * 100. Round to nearest integer.\n"
        "Based on the contract language and exhibits, what is the compliance state for Password Management?"
    ),
    "IT Asset Management": (
        "Check EACH sub-requirement below against the contract. Mark YES only if there is explicit evidence.\n"
        "Sub-requirements (4 total):\n"
        "  1. In-scope asset inventory covering cloud accounts/subscriptions, workloads, databases, security tooling\n"
        "  2. Minimum inventory fields defined\n"
        "  3. At least quarterly reconciliation/review of the inventory\n"
        "  4. Secure configuration baselines with drift remediation and prohibition of insecure defaults\n"
        "HINT: Asset inventory scope may appear in Section 9.1; inventory fields/review in Section 9.2; "
        "configuration baselines in Section 9.3; Exhibit G controls ASSET-01, ASSET-02, ASSET-03 if present.\n"
        "confidence = (number of YES / 4) * 100. Round to nearest integer.\n"
        "Based on the contract language and exhibits, what is the compliance state for IT Asset Management?"
    ),
    "Security Training & Background Checks": (
        "Check EACH sub-requirement below against the contract. Mark YES only if there is explicit evidence.\n"
        "Sub-requirements (4 total):\n"
        "  1. Security awareness training required on hire\n"
        "  2. Security awareness training required at least annually\n"
        "  3. Background screening for personnel with access to Company Data\n"
        "  4. Screening policy maintained with attestation/evidence\n"
        "HINT: Training on hire + annual refresh may appear in GOV-04; background screening "
        "and attestation may appear in GOV-05 or Section 4.3.\n"
        "confidence = (number of YES / 4) * 100. Round to nearest integer.\n"
        "Based on the contract language and exhibits, what is the compliance state for Security Training and Background Checks?"
    ),
    "Data in Transit Encryption": (
        "Check EACH sub-requirement below against the contract. Mark YES only if there is explicit evidence.\n"
        "Sub-requirements (4 total):\n"
        "  1. Encryption using TLS 1.2+ (preferably TLS 1.3) for Company-to-Service traffic\n"
        "  2. TLS encryption for administrative access pathways\n"
        "  3. TLS encryption for Service-to-Subprocessor transfers\n"
        "  4. Certificate management and avoidance of insecure cipher suites\n"
        "HINT: Section 7.2 covers (a) TLS 1.2+ for external/internal traffic, (b) admin pathway encryption, "
        "(c) subprocessor transfer encryption, and certificate/cipher-suite management. Also check CRYP-01/CRYP-02.\n"
        "confidence = (number of YES / 4) * 100. Round to nearest integer.\n"
        "Based on the contract language and exhibits, what is the compliance state for Data in Transit Encryption?"
    ),
    "Network Authentication & Authorization Protocols": (
        "Check EACH sub-requirement below against the contract. Mark YES only if there is explicit evidence.\n"
        "Sub-requirements (4 total):\n"
        "  1. Authentication mechanisms specified (e.g., SAML SSO for users, OAuth/token-based for APIs)\n"
        "  2. MFA required for privileged/production access\n"
        "  3. Secure admin pathways (bastion/secure gateway) with session logging\n"
        "  4. RBAC authorization required\n"
        "HINT: Auth mechanisms may appear in Section 6.7(a)/NET-01; MFA in Section 6.2/IAM-01; "
        "secure admin pathways in Section 6.7(c) or Section 8.2; RBAC in Section 6.7(b)/NET-03.\n"
        "confidence = (number of YES / 4) * 100. Round to nearest integer.\n"
        "Based on the contract language and exhibits, what is the compliance state for Network Authentication and Authorization Protocols?"
    ),
}

# Keywords for TF-IDF context extraction (STRICTLY from COMPLIANCE_REQUIREMENTS only)
QUESTION_KEYWORDS = {
    "Password Management": [
        "password", "password standard", "password length", "password strength",
        "default", "known-compromised",
        "secure storage", "plaintext", "salted hashing",
        "brute-force", "lockout", "rate limiting",
        "password sharing",
        "vaulting", "privileged credentials", "recovery codes",
        "time-based rotation", "break-glass"
    ],
    "IT Asset Management": [
        "in-scope", "asset inventory", "asset", "inventory",
        "cloud accounts", "subscriptions", "workloads", "databases", "security tooling",
        "minimum inventory fields", "inventory fields",
        "quarterly", "reconciliation", "review",
        "secure configuration", "configuration baselines", "drift", "remediation",
        "insecure defaults"
    ],
    "Security Training & Background Checks": [
        "security awareness training", "security awareness", "training", "awareness",
        "on hire", "annually",
        "background screening", "background", "screening", "personnel",
        "Company Data", "access",
        "screening policy", "attestation", "evidence"
    ],
    "Data in Transit Encryption": [
        "encryption", "in transit",
        "TLS 1.2", "TLS 1.3", "TLS",
        "Company-to-Service", "traffic",
        "administrative access", "pathways",
        "Service-to-Subprocessor", "Subprocessor", "transfers",
        "certificate management", "certificate",
        "insecure cipher suites", "cipher suites"
    ],
    "Network Authentication & Authorization Protocols": [
        "authentication", "authentication mechanisms",
        "SAML", "SSO",
        "OAuth", "token-based", "APIs",
        "MFA", "privileged access", "production access",
        "secure admin pathways", "admin pathways", "bastion", "secure gateway",
        "session logging",
        "RBAC", "authorization"
    ],
}

# Compact per-question prompt — kept short to reduce LLM latency
SINGLE_Q_SYSTEM = (
    "You are a strict contract compliance auditor. "
    "For each numbered sub-requirement, check if the contract has EXPLICIT evidence. "
    "Do NOT assume compliance — if a sub-requirement is not explicitly addressed, mark it NO.\n"
    "Return ONLY a JSON object with these keys:\n"
    '  compliance_state: "Fully Compliant" | "Partially Compliant" | "Non-Compliant"\n'
    '  confidence: integer 0-100 = (YES count / total sub-requirements) * 100\n'
    '  relevant_quotes: ["Section X.Y (brief label)", "Exhibit G (ID-01–ID-03)", ...] '
    '— cite ONLY specific section numbers, exhibit IDs, and control IDs where evidence is found\n'
    '  rationale: ONE concise sentence summarising what the contract covers (and any gaps).\n'
    '  Example rationale: "The contract includes provisions for secure authentication protocols, '
    'such as unique user IDs, passwords, and two-factor authentication for remote access."\n'
    'Rules: >=85 → Fully Compliant, 40-84 → Partially Compliant, <40 → Non-Compliant. '
    'Be conservative — missing evidence means NO. Use ONLY the provided context.'
)

SINGLE_Q_USER = """CONTEXT:
{context}

REQUIREMENT:
{requirement}

Respond with ONLY valid JSON:
{{"compliance_state": "...", "confidence": N, "relevant_quotes": [...], "rationale": "..."}}"""
