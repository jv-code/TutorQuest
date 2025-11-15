from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    anthropic_api_key: str
    supabase_url: str
    supabase_key: str
    supabase_service_role_key: str = ""
    daytona_api_key: str
    daytona_api_url: str
    clerk_webhook_secret: str = ""  # Svix webhook secret from Clerk

    class Config:
        env_file = ".env"
        extra = "ignore"
        # Allow reading from environment variables even if .env doesn't exist
        case_sensitive = False

    @property
    def supabase_admin_key(self):
        return self.supabase_service_role_key or self.supabase_key

# Initialize settings with better error handling
try:
    settings = Settings()
except Exception as e:
    print(f"ERROR: Failed to load settings: {e}")
    print("Required environment variables: ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_KEY, DAYTONA_API_KEY, DAYTONA_API_URL")
    raise
