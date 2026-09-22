"""Application configuration loaded from environment / .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_ROOT = PROJECT_ROOT / "data"


class Settings(BaseSettings):
    """Runtime configuration for the MECHORA backend."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "MECHORA API"
    api_v1_prefix: str = "/api/v1"
    debug: bool = False

    # --- Database ---
    # SQLAlchemy URL. Postgres is the production store.
    #   store=auto     -> try Postgres, fall back to a local SQLite file
    #   store=sqlite   -> always SQLite (offline demo / tests)
    #   store=postgres -> require Postgres
    database_url: str = "postgresql+psycopg://mechora:mechora@localhost:5432/mechora"
    store: str = "auto"
    sqlite_fallback_path: str = str(DATA_ROOT / "mechora_dev.db")

    # --- AI ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    extraction_provider: str = "auto"  # auto | llm | rules
    embedding_model: str = ""  # optional sentence-transformers model

    # --- Precursor engine ---
    family_assign_threshold: float = 0.65
    embedding_blend: float = 0.05  # max supporting weight for embeddings
    recurring_min_observations: int = 2  # explicit recurring threshold
    family_exclusion_floor: float = 0.35  # min similarity to report a WHY-NOT pair

    report_id_prefix: str = "OBS"

    # --- Document upload ---
    # Uploaded report files (PDF/DOCX/TXT) are validated against these caps.
    # The character budget aligns with the AnalyzeRequest.narrative max_length so
    # extracted text always fits the existing single analysis path.
    max_upload_bytes: int = 15 * 1024 * 1024  # max raw upload size (15 MB)
    max_document_characters: int = 3000  # max extracted text given to the analyzer

    # --- Security / authentication (MVP bearer-token demo auth) ---
    # When enabled, every /api/v1 data route requires a valid bearer token
    # issued by POST /auth/login. Credentials are demo-only; the password is
    # verified against a PBKDF2-HMAC-SHA256 hash (never stored or logged in
    # plaintext). AUTH_PASSWORD_HASH (format pbkdf2_sha256$rounds$salt$hash)
    # takes precedence over AUTH_PASSWORD. AUTH_SECRET signs tokens; when left
    # blank a random in-memory secret is generated at startup.
    auth_enabled: bool = True
    auth_email: str = "hse.analyst@oilindia.in"
    auth_password: str = ""
    auth_password_hash: str = ""
    auth_secret: str = ""
    auth_identity_name: str = "HSE Safety Analyst"
    auth_identity_role: str = "HSE Field Analyst / SIH Evaluator"
    auth_identity_organization: str = "Oil India Limited (OIL)"
    auth_token_ttl_hours: float = 8.0
    auth_max_attempts: int = 10
    auth_lockout_seconds: int = 300

    @property
    def sqlite_fallback_url(self) -> str:
        return f"sqlite:///{Path(self.sqlite_fallback_path).as_posix()}"

    @property
    def data_root(self) -> Path:
        return DATA_ROOT

    @property
    def ontology_root(self) -> Path:
        return DATA_ROOT / "ontology"

    @property
    def eval_set_path(self) -> Path:
        return DATA_ROOT / "evaluation" / "eval_set.json"

    @property
    def dev_set_path(self) -> Path:
        return DATA_ROOT / "synthetic" / "dev_set.json"

    @property
    def eval_results_path(self) -> Path:
        return DATA_ROOT / "evaluation" / "results"


@lru_cache
def get_settings() -> Settings:
    return Settings()