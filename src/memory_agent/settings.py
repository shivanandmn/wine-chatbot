import logging
import os
from pathlib import Path

import dotenv
from pydantic import EmailStr, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s  %(message)s", level=logging.DEBUG)
logging.getLogger("passlib.handlers.bcrypt").setLevel(logging.ERROR)


class Settings(BaseSettings):
    """
    Settings that are the same in all environments are provided as defaults.

    Settings that vary between environments have no default. They are provided by environment-specific .env files, checked into Git.

    Secrets have a comment: `# secret`. They are provided as env vars at runtime. They have no default so they cannot be missed.
    """

    env_name: str  # environment that these settings are for

    enable_ai_mocking: bool = False  # enable mocking ai service for development

    # assets
    project_root: Path = list(Path(__file__).parents)[2]
    asset_dir: Path = project_root / "asset"
    data_dir: Path = project_root / "data"
    credentials_dir: Path = asset_dir / "credentials"
    template_dir: Path = asset_dir / "templates"
    weight_dir: Path = asset_dir / "weights"
    prompt_dir: Path = asset_dir / "prompts"
    grammar_data_dir: Path = asset_dir / "grammar_data"

    # app
    home_page: str
    image_host: str = "https://vinovoss.com"
    user_browsing_history_max: int = 200  # max number of wines to be displayed in user browsing history
    shared_list_max_size: int = 200  # max number of wines to be displayed in a shared list
    rating_count_pivots: list[int] = [0, 12, 35, 94, 294]  # to ranking wines by rating count in the scale of 1-5

    # jwt tokens
    jwt_secret: SecretStr  # secret
    jwt_access_token_lifetime_seconds: int = 3600  # 1 hour
    jwt_refresh_token_lifetime_seconds: int = 3600 * 24 * 90  # 90 days

    # logging
    log_level: int = logging.DEBUG
    log_format: str = "%(levelname)-8s %(message)s"

    # caching
    backend_cache_host: str = "backend_cache"
    backend_cache_port: int = 6379
    deployment_type: str = "prod"
    db_change_poll_interval: int = 30  # seconds
    default_cache_ttl: int = 30 * 60  # 30 minutes

    # histogram config
    phv_max: int = 200  # price histogram value(phv) max
    histogram_steps: int = 20
    histogram_scale: int = 10
    price_histogram_max_length: int = 200

    # blogging
    default_author: str = "Vinovoss Publication"
    blog_cache_ttl: int = 60  # seconds
    medium_cdn: str = "https://cdn-images-1.medium.com"
    medium_post: str = "https://medium.com/p"
    top_searched_query_endpoint: str = "api/v2/menu/top_searched_queries"

    # Login with Google
    google_oauth_client_id: str = "533877371912-hsn3ennj2nkqevjpl6utftqlt2drl7kr.apps.googleusercontent.com"
    google_oauth_client_secret: SecretStr  # secret
    google_callback: str
    # Google + iOS
    google_oauth_ios_client_id: str = (
        "533877371912-2udhd6obsueq7j6bkqcii9qtttvhdcj3.apps.googleusercontent.com"  # different on dev
    )
    # Google + Android
    google_oauth_android_client_id: list[str] = [
        "533877371912-hd6b4vgk01md1b6jrrds0n3odkbdps50.apps.googleusercontent.com",
        "533877371912-0du0ibn5ko0p1pnhv8lv7ucf4cb7oh8r.apps.googleusercontent.com",
    ]  # different on dev

    # Login with Apple
    apple_native_client_id: str = "com.vinovoss"  # different on dev
    apple_web_client_id: str = "com.vinovoss.apple"  # configured here: https://developer.apple.com/account/resources/identifiers/list/serviceId
    apple_web_callback_url: str = "https://vinovoss.com/apple/callback"  # different on dev
    apple_web_login_key_id: str = "CHP292DL6D"
    apple_login_key_secret: SecretStr = SecretStr("secret")
    apple_team_id: str = "72DCYV8FAB"

    # Public cloud bucket
    gcp_project_id: str = "w266-project-329918"
    service_account_credential: Path = credentials_dir / "w266-project-329918-343bc0b68293.json"
    gcp_storage_endpoint: str = "https://storage.googleapis.com"
    gcp_storage_bucket: str = "drinkbetter"
    gcp_storage_bottle_images_dir: str = "images/bottles"
    gcp_storage_avatar_dir: str = "users-avatar"
    gcp_storage_user_uploaded_bottle_dir: str = "images/user_uploaded"
    gcp_storage_blog_image_dir: str = "images/blog"
    image_extension: str = ".webp"

    # User data cloud bucket
    gcp_user_data_bucket_name: str = "vinovoss_user_data"
    gcp_user_data_drinking_history_dir: str = "drinking_history_images"
    gcp_user_data_web_event_dir: str = "web_event_images"
    gcp_user_data_cv_dir: str = "users-cv"

    # networking between services
    default_ai_host: str = "ai"
    default_ai_port: int = 80
    http_request_timeout: int = 10  # seconds
    meta_service_endpoint: str = "http://meta-worker/meta"

    # email
    mail_username: str = "info@vinovoss.com"
    mail_password: SecretStr  # secret
    # TODO: would be good to change this to use support@vinovoss.com
    mail_from: EmailStr = "info@vinovoss.com"
    mail_port: int = 465
    mail_server: str = "smtppro.zoho.com"
    mail_from_name: str = "VinoVoss"
    mail_tls: bool = False
    mail_ssl: bool = True
    use_credentials: bool = True
    validate_certs: bool = True

    owner_emails: list[EmailStr] = ["shawn.dev.vn@gmail.com", "vinovoss.01@gmail.com"]
    new_review_notification_email: EmailStr = "timevinovoss@gmail.com"

    # postgres config
    postgres_host: str
    postgres_port: int = 5432
    postgres_database: str = "private_dataset"
    postgres_user: str = "app__vinovoss_backend"
    postgres_password: SecretStr  # secret
    postgres_max_connections: int = 12
    postgres_init_connections: int = 2

    # mongodb config
    db_connection_string: SecretStr  # secret

    # Mapbox - reverse geocoding
    mapbox_api_key: SecretStr  # secret

    # IPInfo - IP address to location
    ipinfo_api_key: SecretStr = SecretStr("secret")

    # OpenAI key
    openai_api_key: SecretStr = SecretStr("secret")

    # Event publishing to Pub/Sub
    event_publishing_enabled: bool

    # Image search backend
    image_search_backend_host: str

    # Superficial access control on endpoint used for uptime check
    internal_endpoint_token: str = "MQM3gRTamwcetZ"

    # SmartSomm
    smartsomm_ai_endpoint: str = "https://api.deepinfra.com/v1/openai"
    smartsomm_ai_api_key: str = "ai_api_key"
    smartsomm_ai_model: str = "gemini-2.5-flash-preview-04-17"
    smartsomm_router_prompt_path: str | None = None
    gemini_api_key: str | None = None
    openai_max_retry: int = 5
    chat_history_database: str = "private_dataset"
    chat_history_table: str = "chat_history"
    stop_command: str = "stop"
    voice_mode_on_command: str = "voice-mode-on"
    voice_mode_off_command: str = "voice-mode-off"
    smartsomm_ws_endpoint: str = "ws://localhost:8000/api/v2/copilot/websocket"
    smartsomm_interaction_limit: int = 10

    # Doc User
    doc_user: str = "vinovoss"
    doc_user_password: str = "vinovossdev!@#$%"

    # Marketplace and CRM integration
    marketplace_enabled: bool = False
    medusa_api_key_public: str = "medusa_api_key_public"
    medusa_api_key_secret: SecretStr = SecretStr("secret")
    medusa_api_base_url: str = "http://localhost:9000"

    # LangChain settings
    langsmith_api_key: str | None = None
    langsmith_project: str | None = None
    langchain_tracing_v2: bool = False
    langchain_endpoint: str | None = None
    google_api_key: str | None = None

    model_config = SettingsConfigDict(case_sensitive=False)


ENV_VAR_NAME = "ENV_NAME"
ENV_VALUE_TO_FILE_MAP: dict[str, str] = {
    "prod": "settings_prod.env",
    "dev": "settings_dev.env",
    "cloudrun_dev": "settings_cloudrun_dev.env",
    "cloudrun_prod": "settings_cloudrun_prod.env",
    "cloudrun_staging": "settings_cloudrun_staging.env",
    "test": "settings_test.env",
}


def get_settings() -> Settings:
    logging.info(f"get_settings() - Looking for {ENV_VAR_NAME} in environment...")
    env = os.getenv(ENV_VAR_NAME, "dev")
    logging.info(f"get_settings() - Using environment: {env}")

    # Default configuration for development/demo environment
    default_config = {
        "env_name": "dev",
        "home_page": "http://localhost:8501",
        "jwt_secret": "dev-secret-key",
        "google_oauth_client_secret": "",
        "google_callback": "http://localhost:8501/callback",
        "mail_password": "",
        "postgres_host": "localhost",
        "postgres_password": "",
        "db_connection_string": "sqlite:///demo.db",  # Use SQLite for demo
        "event_publishing_enabled": "False",
        "image_search_backend_host": "http://localhost:8009",
        "mapbox_api_key": ""
    }

    # Try to find .env file
    dotenv_path = dotenv.find_dotenv(usecwd=True)
    if not dotenv_path:
        logging.warning("No .env file found. Using default development configuration.")
        return Settings(**default_config)

    # Read and parse the .env file
    config = {}
    current_section = None
    
    with open(dotenv_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            if line.startswith('[') and line.endswith(']'):
                current_section = line[1:-1]
                continue
                
            if '=' in line:
                key, value = [x.strip() for x in line.split('=', 1)]
                # Remove quotes if present
                value = value.strip('"')
                
                # Flatten the key with section prefix if in a section
                if current_section:
                    key = f"{current_section}_{key}"
                
                config[key.lower()] = value

    # Merge with defaults
    merged_config = default_config.copy()
    merged_config.update({
        "google_oauth_client_secret": config.get('google_oauth_client_secret', ''),
        "google_callback": config.get('google_callback', default_config['google_callback']),
        "mail_password": config.get('mail_password', ''),
        "postgres_host": config.get('postgres_host', default_config['postgres_host']),
        "postgres_password": config.get('postgres_password', ''),
        "db_connection_string": config.get('mongodb_connection_string', default_config['db_connection_string']),
        "env_name": config.get('app_env_name', default_config['env_name']),
        "home_page": config.get('app_home_page', default_config['home_page']),
        "event_publishing_enabled": config.get('app_event_publishing_enabled', default_config['event_publishing_enabled']),
        "image_search_backend_host": config.get('ai_image_search_backend_host', default_config['image_search_backend_host']),
        "jwt_secret": config.get('app_jwt_secret', default_config['jwt_secret']),
        "mapbox_api_key": config.get('app_mapbox_api_key', default_config['mapbox_api_key'])
    })

    return Settings(**merged_config)
