import os
from datetime import time
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


def database_uri():
    user = quote_plus(os.environ.get("MYSQL_USER", "root"))
    password = quote_plus(os.environ.get("MYSQL_PASSWORD", ""))
    host = os.environ.get("MYSQL_HOST", "localhost")
    port = os.environ.get("MYSQL_PORT", "3306")
    name = os.environ.get("MYSQL_DATABASE", "dental_clinic")
    return (
        f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"
        "?charset=utf8mb4"
    )


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "connect_args": {"charset": "utf8mb4"},
    }
    CLINIC_OPEN = time(8, 0)
    CLINIC_CLOSE = time(20, 0)
    SLOT_MINUTES = 30
    JSON_AS_ASCII = False
