from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DB_HOST: str = "10.100.54.176"
    DB_NAME: str = "ALRIMI"
    DB_USER: str = "root"
    DB_PASSWORD: str = "ibdp"
    DB_PORT: int = 3306

    class Config:
        env_file = ".env"

settings = Settings()