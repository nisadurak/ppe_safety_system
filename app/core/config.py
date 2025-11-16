import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings:
    PROJECT_NAME: str = "PPE Safety System"
    UPLOAD_DIR: str = os.path.join(BASE_DIR, "uploads")

    def __init__(self) -> None:
       
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)


settings = Settings()
