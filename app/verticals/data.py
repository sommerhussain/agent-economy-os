from app.verticals.base import CredentialPack, CredentialDefinition

DataCredentialPack = CredentialPack(
    pack_id="data",
    name="Data & Compute",
    description="Core credentials for data access, AI compute, and cloud infrastructure.",
    credentials={
        "google_api": CredentialDefinition(
            name="Google API Key",
            description="Access to Google Cloud and Workspace APIs.",
            allowed_scopes=["drive:read", "drive:write", "cloud:compute"]
        ),
        "openai_api": CredentialDefinition(
            name="OpenAI API Key",
            description="Access to OpenAI language models.",
            allowed_scopes=["model:read", "model:execute", "fine_tune:write"]
        ),
        "aws_access": CredentialDefinition(
            name="AWS Access Key",
            description="AWS programmatic access credentials.",
            allowed_scopes=["s3:read", "s3:write", "ec2:manage"]
        ),
        "web_scraper": CredentialDefinition(
            name="Web Scraper Proxy",
            description="Premium residential proxy for web scraping.",
            allowed_scopes=["proxy:http", "proxy:https", "scrape:js"]
        )
    }
)
