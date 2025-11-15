from supabase import create_client, Client
try:
    import config
    from config import settings
except ModuleNotFoundError:
    from src.config import settings

supabase: Client = create_client(settings.supabase_url, settings.supabase_admin_key)
