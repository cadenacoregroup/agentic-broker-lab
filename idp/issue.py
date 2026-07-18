"""Mock IdP: mints identity tokens for users and agents.
Phase 1 replaces this file entirely with real Entra ID sign-in and
service-principal tokens; nothing downstream should need to change."""
import time, jwt, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from common.config import IDP_SECRET, IDP_ISSUER

def mint(subject: str, subject_type: str, ttl: int = 3600) -> str:
    now = int(time.time())
    return jwt.encode(
        {"iss": IDP_ISSUER, "sub": subject, "typ": subject_type,
         "iat": now, "exp": now + ttl},
        IDP_SECRET, algorithm="HS256")

def user_token(upn: str) -> str: return mint(upn, "user")
def agent_token(agent_id: str) -> str: return mint(agent_id, "agent")

if __name__ == "__main__":
    print("maria :", user_token("maria@cadenacore.dev"))
    print("agent :", agent_token("invoice-agent-01"))
