"""Phase 0 configuration. In Phase 1, IDP_SECRET validation is replaced by
Entra ID JWKS validation, and BROKER mints via OAuth token exchange."""
IDP_SECRET = "phase0-mock-idp-secret"        # stands in for Entra ID
BROKER_SECRET = "phase0-broker-signing-key"  # broker's own signing key
IDP_ISSUER = "mock-idp"
BROKER_ISSUER = "cadena-broker"
ERP_AUDIENCE = "erp-api"
BROKER_URL = "http://127.0.0.1:8001"
ERP_URL = "http://127.0.0.1:8002"
AUDIT_LOG = "audit/audit.jsonl"
