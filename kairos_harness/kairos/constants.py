from __future__ import annotations

SCHEMA_VERSION = "kairos-context/v1"
DATABASE_SCHEMA_VERSION = "kairos-db/v1"
RUNTIME_SCHEMA_VERSION = "kairos-runtime/v1"
GOAL_SCHEMA_VERSION = "kairos-goal/v1"

MAX_HEADER_BYTES = 3_072
FIRST_WINDOW_BYTES = 4_096
MAX_CAPSULE_CHARS = 480
MAX_CLAIM_BOUNDARY_CHARS = 480
MAX_PRIMARY_REFS = 8
MAX_ANSWER_HANDLES = 10
MAX_DOCUMENT_BYTES = 2 * 1024 * 1024
MAX_SECTION_BYTES = 256 * 1024
MAX_SECTIONS = 128
MAX_REFERENCES = 256
MAX_QUERY_CHARS = 4096
MAX_SEARCH_RESULTS = 50
MAX_SEARCH_CANDIDATES = 500
MAX_CONTEXT_HOPS = 4
MAX_CONTEXT_CHASE_RESULTS = 50
MAX_RETRIEVAL_TRACES = 1000
MAX_GOVERNED_ACTION_RECEIPTS = 10_000
MAX_GOVERNANCE_VIOLATIONS = 2_000
MAX_QUARANTINE_HISTORY = 2_000
MAX_TERMINAL_ACTION_PERMITS = 12_000
MAX_DYNAMIC_TASK_POINTERS = 8
MAX_DYNAMIC_CRITERION_POINTERS = 12
MAX_GENERATED_RECEIPT_FILES = 200
MAX_MANAGED_DOCUMENTS = 10_000
MAX_MANAGED_SOURCE_BYTES = 256 * 1024 * 1024
MAX_GOAL_FILES = 1024
MAX_GOAL_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_GOAL_BYTES = 64 * 1024 * 1024
MAX_MILESTONES_PER_GOAL = 256
MAX_CRITERIA_PER_GOAL = 4096
MAX_GOAL_TEXT_CHARS = 8192
MAX_BACKUP_SOURCE_FILES = MAX_MANAGED_DOCUMENTS + MAX_GOAL_FILES + 16
MAX_BACKUP_SOURCE_BYTES = MAX_MANAGED_SOURCE_BYTES + MAX_TOTAL_GOAL_BYTES + 32 * 1024 * 1024
MAX_BACKUP_MANIFEST_BYTES = 16 * 1024 * 1024

EVIDENCE_DOCUMENT_TYPES = {
    "report",
    "bug",
    "code",
    "decision",
    "research",
    "archive",
    "documentation",
}

DOCUMENT_TYPES = {
    "task",
    "report",
    "bug",
    "code",
    "decision",
    "research",
    "archive",
    "router",
    "gate",
    "session",
    "documentation",
}

LIFECYCLE_STATES = {
    "new",
    "ready",
    "active",
    "in_progress",
    "partial",
    "success",
    "failed",
    "blocked",
    "resolved",
    "completed",
    "superseded",
    "finalized",
}

RELATION_TYPES = {
    "about",
    "belongs_to",
    "caused_by",
    "contradicts",
    "depends_on",
    "derived_from",
    "documents",
    "evidenced_by",
    "fixes",
    "implemented_by",
    "implements",
    "informs",
    "next",
    "parent",
    "produces",
    "references",
    "requires",
    "resolves",
    "satisfies",
    "supports",
    "supersedes",
    "unblocks",
    "validated_by",
    "validates",
}

ACQUISITION_MODES = {"auto", "work", "depth", "breadth", "breathe", "verify"}

AUTHORITIES = {
    "architecture_authority",
    "diagnostic_record",
    "execution_evidence",
    "goal_authority",
    "implementation_documentation",
    "loop_archive",
    "operating_contract",
    "research_evidence",
    "routing",
    "state_authority",
    "task_contract",
    "validation_evidence",
}

DOCUMENT_TYPE_AUTHORITIES = {
    "task": {"task_contract"},
    "report": {"execution_evidence", "validation_evidence"},
    "bug": {"diagnostic_record"},
    "code": {"implementation_documentation"},
    "decision": {"architecture_authority"},
    "research": {"research_evidence"},
    "archive": {"loop_archive"},
    "router": {"routing"},
    "gate": {"state_authority"},
    "session": {"routing"},
    "documentation": {"architecture_authority", "operating_contract"},
}

DEFAULT_DOCUMENT_ROOTS = [
    "tasks",
    "reports",
    "bugs",
    "code",
    "decisions",
    "research",
    "docs",
    "archive",
]

DEFAULT_CANONICAL_FILES = [
    "AGENTS.md",
    "NEURAL_CORTEX.md",
    "ACTIVE.md",
    "CLOSED.md",
    "_LOOP_GATE.md",
    "_SESSION.md",
]

DYNAMIC_CANONICAL_FILES = {
    "NEURAL_CORTEX.md",
    "ACTIVE.md",
    "CLOSED.md",
    "_LOOP_GATE.md",
    "_SESSION.md",
}
