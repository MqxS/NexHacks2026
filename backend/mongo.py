import os
from typing import Any
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from pymongo.server_api import ServerApi

_client: MongoClient | None = None

def connect(timeout_ms: int = 5000) -> Any:
    global _client
    uri = os.getenv("MONGO_URI")
    db_name = os.getenv("MONGO_DB")

    if not uri:
        raise RuntimeError("MONGO_URI environment variable is not set")
    if not db_name:
        raise RuntimeError("MONGO_DB environment variable is not set")

    if _client is None:
        _client = MongoClient(
            uri,
            tls=True,
            tlsAllowInvalidCertificates=True,
            serverSelectionTimeoutMS=timeout_ms,
            server_api=ServerApi('1')
        )
        try:
            _client.admin.command("ping")
        except ServerSelectionTimeoutError as exc:
            _client = None
            raise RuntimeError("Unable to connect to MongoDB") from exc
        print("Connected To MongoDB!")

    return _client[db_name]
