from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, ValidationError, PositiveInt
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):

    # Database Settings
    DATABASE_NAME: str = Field(..., env="DATABASE_NAME")  # type: ignore
    DATABASE_USER: str = Field(..., env="DATABASE_USER")  # type: ignore
    DATABASE_PASSWORD: str = Field(..., env="DATABASE_PASSWORD")  # type: ignore
    DATABASE_HOST: str = Field(..., env="DATABASE_HOST")  # type: ignore
    DATABASE_PORT: PositiveInt = Field(..., env="DATABASE_PORT")  # type: ignore

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


if __name__ == "__main__":
    try:
        settings = Settings()  # type: ignore
        print("Configuración cargada exitosamente:")
        for field in [
            "DATABASE_NAME",
            "DATABASE_USER",
            "DATABASE_PASSWORD",
            "DATABASE_HOST",
            "DATABASE_PORT",
        ]:
            print(f"  {field}: {getattr(settings, field)}")

    except ValidationError as e:
        print("❌ Error de configuración de variables de entorno:")
        for err in e.errors():
            loc = ".".join(str(x) for x in err["loc"])
            msg = err["msg"]
            print(f"  - {loc}: {msg}")

settings = Settings()  # type: ignore
