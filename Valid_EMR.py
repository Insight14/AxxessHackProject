"""
EMR Document Validator
Validates documents against standard EMR requirements:
1. Unique Identifiers (Patient Name, DOB, MRN, Insurance)
2. SOAP Workflow (Subjective, Objective, Assessment, Plan)
3. Post-Encounter Instructions (Medications, Follow-up, Emergency Contact)
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Tuple


@dataclass
class ValidationResult:
    """Stores validation results for a single category."""
    category: str
    passed: bool
    score: float  # 0.0 to 1.0
    found_items: List[str] = field(default_factory=list)
    missing_items: List[str] = field(default_factory=list)
    details: str = ""


@dataclass
class EMRValidationReport:
    """Complete validation report for an EMR document."""
    is_valid: bool
    overall_score: float  # 0.0 to 1.0
    identifiers: ValidationResult = None
    soap_workflow: ValidationResult = None
    post_encounter: ValidationResult = None
    
    def to_dict(self) -> Dict:
        return {
            "is_valid": self.is_valid,
            "overall_score": round(self.overall_score * 100, 1),
            "identifiers": {
                "passed": self.identifiers.passed,
                "score": round(self.identifiers.score * 100, 1),
                "found": self.identifiers.found_items,
                "missing": self.identifiers.missing_items,
                "details": self.identifiers.details
            },
            "soap_workflow": {
                "passed": self.soap_workflow.passed,
                "score": round(self.soap_workflow.score * 100, 1),
                "found": self.soap_workflow.found_items,
                "missing": self.soap_workflow.missing_items,
                "details": self.soap_workflow.details
            },
            "post_encounter": {
                "passed": self.post_encounter.passed,
                "score": round(self.post_encounter.score * 100, 1),
                "found": self.post_encounter.found_items,
                "missing": self.post_encounter.missing_items,
                "details": self.post_encounter.details
            }
        }


class EMRValidator:
    """Validates EMR documents for completeness and compliance."""
    
    # ===== IDENTIFIER PATTERNS =====
    IDENTIFIER_PATTERNS = {
        "Patient Name": [
            r"patient\s*name\s*[:\-]?\s*([A-Za-z\s\-\'\.]+)",
            r"name\s*[:\-]?\s*([A-Za-z]+\s+[A-Za-z]+)",
            r"patient\s*[:\-]?\s*([A-Za-z]+\s+[A-Za-z]+)",
        ],
        "Date of Birth": [
            r"(?:dob|date\s*of\s*birth|birth\s*date|d\.o\.b\.?)\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
            r"(?:dob|date\s*of\s*birth)\s*[:\-]?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
            r"born\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        ],
        "Medical Record Number": [
            r"(?:mrn|medical\s*record\s*(?:number|no\.?|#)?|record\s*(?:number|no\.?|#)?|chart\s*(?:number|no\.?|#)?)\s*[:\-]?\s*([A-Za-z0-9\-]+)",
            r"(?:pcc|patient\s*id|id)\s*[#:\-]?\s*(\d+)",
        ],
        "Insurance": [
            r"(?:insurance|insurer|payer|coverage)\s*[:\-]?\s*([A-Za-z\s\-]+)",
            r"(?:policy|member)\s*(?:number|no\.?|#|id)\s*[:\-]?\s*([A-Za-z0-9\-]+)",
            r"(?:medicare|medicaid|blue\s*cross|aetna|cigna|united\s*health)",
        ],
        "Visit Date": [
            r"(?:visit|encounter|appointment|date\s*of\s*service|dos)\s*(?:date)?\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
            r"(?:seen\s*on|visited\s*on)\s*[:\-]?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        ],
        "Provider Name": [
            r"(?:provider|physician|doctor|dr\.?|attending|clinician)\s*[:\-]?\s*([A-Za-z\s\-\'\.]+(?:md|m\.d\.?|do|d\.o\.?|np|pa|rn)?)",
            r"(?:seen\s*by|treated\s*by)\s*[:\-]?\s*([A-Za-z\s\-\'\.]+)",
        ],
    }
    
    # ===== SOAP WORKFLOW PATTERNS =====
    # S - Subjective (Chief Complaint, History)
    # O - Objective (Vitals, Physical Exam, Labs)
    # A - Assessment (Diagnosis)
    # P - Plan (Treatment Plan)
    SOAP_PATTERNS = {
        "Chief Complaint": [
            r"(?:chief\s*complaint|cc|presenting\s*complaint|reason\s*for\s*visit|complaint)\s*[:\-]?",
            r"(?:patient\s*(?:presents|presented|complains|reports)\s*(?:with|of))",
        ],
        "History": [
            r"(?:history\s*of\s*present\s*illness|hpi|medical\s*history|history|past\s*medical\s*history|pmh)\s*[:\-]?",
            r"(?:patient\s*history|clinical\s*history|presenting\s*history)\s*[:\-]?",
        ],
        "Vital Signs": [
            r"(?:vital\s*signs?|vitals)\s*[:\-]?",
            r"(?:blood\s*pressure|bp|heart\s*rate|hr|pulse|temperature|temp|respiratory\s*rate|rr|oxygen\s*saturation|spo2|o2\s*sat)\s*[:\-]?\s*[\d\.]+",
            r"(?:weight|height|bmi)\s*[:\-]?\s*[\d\.]+",
        ],
        "Physical Exam": [
            r"(?:physical\s*exam(?:ination)?|pe|exam(?:ination)?|objective)\s*[:\-]?",
            r"(?:general\s*appearance|heent|cardiovascular|respiratory|abdomen|extremities|neurological)\s*[:\-]?",
        ],
        "Labs/Tests": [
            r"(?:lab(?:oratory)?(?:\s*results?)?|test(?:\s*results?)?|diagnostics?|imaging|x-?ray|mri|ct\s*scan)\s*[:\-]?",
            r"(?:cbc|bmp|cmp|urinalysis|culture|rapid\s*strep|strep\s*test)\s*[:\-]?",
        ],
        "Assessment": [
            r"(?:assessment|diagnosis|diagnoses|impression|clinical\s*impression|dx)\s*[:\-]?",
            r"(?:icd[\-\s]?\d{1,2}|diagnosis\s*code)\s*[:\-]?",
        ],
        "Plan": [
            r"(?:plan|treatment\s*plan|management|recommendations?|orders?)\s*[:\-]?",
            r"(?:will\s*(?:prescribe|order|recommend|refer)|advised\s*to|instructed\s*to)",
        ],
    }
    
    # ===== POST-ENCOUNTER PATTERNS =====
    POST_ENCOUNTER_PATTERNS = {
        "Medications": [
            r"(?:medication|medications|rx|prescription|prescribe[ds]?|med(?:s)?)\s*[:\-]?",
            r"(?:take|taking|start(?:ed)?|continue|discontinue)\s+[\w\s]+\s+(?:\d+\s*mg|\d+\s*ml)",
            r"(?:prn|bid|tid|qid|qd|daily|twice\s*daily|as\s*needed)",
            r"(?:amoxicillin|ibuprofen|acetaminophen|tylenol|advil|antibiotic)",
        ],
        "Follow-up": [
            r"(?:follow[\-\s]?up|f\/u|return\s*visit|next\s*(?:visit|appointment)|recheck)\s*[:\-]?",
            r"(?:return\s*(?:in|to)|come\s*back|schedule|scheduled\s*for)\s*(?:\d+\s*(?:days?|weeks?|months?))?",
            r"(?:if\s*(?:symptoms?\s*)?(?:persist|worsen|not\s*improv))",
        ],
        "Emergency Instructions": [
            r"(?:emergency|emergencies|er|urgent|warning\s*signs?|red\s*flags?|seek\s*(?:immediate|medical))\s*[:\-]?",
            r"(?:go\s*to\s*(?:the\s*)?(?:er|emergency|hospital)|call\s*911|seek\s*immediate)",
            r"(?:if\s*(?:you\s*)?(?:experience|develop|notice|have))\s*(?:severe|worsening|difficulty|chest\s*pain|shortness\s*of\s*breath)",
        ],
        "Patient Education": [
            r"(?:patient\s*education|instructions?|home\s*care|self[\-\s]?care|discharge\s*instructions?)\s*[:\-]?",
            r"(?:rest|fluids|hydration|ice|elevate|avoid)",
        ],
    }
    
    # Minimum required items for each category
    MIN_IDENTIFIERS = 4  # Need at least 4 identifiers (67%)
    MIN_SOAP_SECTIONS = 4  # Need at least 4 SOAP sections (57%)
    MIN_POST_ENCOUNTER = 3  # Need at least 3 post-encounter items (75%)
    
    def __init__(self, document_text: str):
        """Initialize validator with document text."""
        self.document = document_text
        self.document_lower = document_text.lower()
    
    def _check_patterns(self, patterns_dict: Dict[str, List[str]]) -> Tuple[List[str], List[str]]:
        """Check document against a dictionary of patterns."""
        found = []
        missing = []
        
        for item_name, patterns in patterns_dict.items():
            item_found = False
            for pattern in patterns:
                if re.search(pattern, self.document_lower, re.IGNORECASE):
                    item_found = True
                    break
            
            if item_found:
                found.append(item_name)
            else:
                missing.append(item_name)
        
        return found, missing
    
    def validate_identifiers(self) -> ValidationResult:
        """
        Step 1: Check for unique identifiers.
        Required: Patient Name, DOB, MRN, Insurance, Visit Date, Provider
        """
        found, missing = self._check_patterns(self.IDENTIFIER_PATTERNS)
        
        total_items = len(self.IDENTIFIER_PATTERNS)
        score = len(found) / total_items if total_items > 0 else 0
        passed = len(found) >= self.MIN_IDENTIFIERS
        
        details = f"Found {len(found)}/{total_items} identifiers. "
        if passed:
            details += "✓ Sufficient identifiers present."
        else:
            details += f"✗ Need at least {self.MIN_IDENTIFIERS} identifiers."
        
        return ValidationResult(
            category="Unique Identifiers",
            passed=passed,
            score=score,
            found_items=found,
            missing_items=missing,
            details=details
        )
    
    def validate_soap_workflow(self) -> ValidationResult:
        """
        Step 2: Check SOAP workflow compliance.
        S - Subjective: Chief Complaint, History
        O - Objective: Vitals, Physical Exam, Labs
        A - Assessment: Diagnosis
        P - Plan: Treatment Plan
        """
        found, missing = self._check_patterns(self.SOAP_PATTERNS)
        
        total_items = len(self.SOAP_PATTERNS)
        score = len(found) / total_items if total_items > 0 else 0
        passed = len(found) >= self.MIN_SOAP_SECTIONS
        
        # Check SOAP coverage
        soap_coverage = {
            "Subjective": any(item in found for item in ["Chief Complaint", "History"]),
            "Objective": any(item in found for item in ["Vital Signs", "Physical Exam", "Labs/Tests"]),
            "Assessment": "Assessment" in found,
            "Plan": "Plan" in found,
        }
        
        soap_present = [k for k, v in soap_coverage.items() if v]
        soap_missing = [k for k, v in soap_coverage.items() if not v]
        
        details = f"Found {len(found)}/{total_items} SOAP elements. "
        details += f"SOAP Coverage: {', '.join(soap_present) if soap_present else 'None'}. "
        if passed:
            details += "✓ Adequate SOAP workflow."
        else:
            details += f"✗ Missing: {', '.join(soap_missing)}."
        
        return ValidationResult(
            category="SOAP Workflow",
            passed=passed,
            score=score,
            found_items=found,
            missing_items=missing,
            details=details
        )
    
    def validate_post_encounter(self) -> ValidationResult:
        """
        Step 3: Check for post-encounter instructions.
        Required: Medications, Follow-up, Emergency Instructions, Patient Education
        """
        found, missing = self._check_patterns(self.POST_ENCOUNTER_PATTERNS)
        
        total_items = len(self.POST_ENCOUNTER_PATTERNS)
        score = len(found) / total_items if total_items > 0 else 0
        passed = len(found) >= self.MIN_POST_ENCOUNTER
        
        details = f"Found {len(found)}/{total_items} post-encounter elements. "
        if passed:
            details += "✓ Adequate post-encounter instructions."
        else:
            details += f"✗ Need at least {self.MIN_POST_ENCOUNTER} post-encounter items."
        
        return ValidationResult(
            category="Post-Encounter Instructions",
            passed=passed,
            score=score,
            found_items=found,
            missing_items=missing,
            details=details
        )
    
    def validate(self) -> EMRValidationReport:
        """
        Run complete EMR validation.
        Returns a comprehensive validation report.
        """
        # Run all validations
        identifiers = self.validate_identifiers()
        soap = self.validate_soap_workflow()
        post_encounter = self.validate_post_encounter()
        
        # Calculate overall score (weighted average)
        # Identifiers: 30%, SOAP: 50%, Post-Encounter: 20%
        overall_score = (
            identifiers.score * 0.30 +
            soap.score * 0.50 +
            post_encounter.score * 0.20
        )
        
        # Document is valid if all three categories pass
        is_valid = identifiers.passed and soap.passed and post_encounter.passed
        
        return EMRValidationReport(
            is_valid=is_valid,
            overall_score=overall_score,
            identifiers=identifiers,
            soap_workflow=soap,
            post_encounter=post_encounter
        )


def validate_emr_document(document_text: str) -> Dict:
    """
    Main function to validate an EMR document.
    
    Args:
        document_text: The text content of the EMR document
        
    Returns:
        Dictionary containing validation results
    """
    validator = EMRValidator(document_text)
    report = validator.validate()
    return report.to_dict()
