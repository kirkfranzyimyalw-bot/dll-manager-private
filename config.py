import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-secret-key')
    
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    UPLOAD_FOLDER_TESTING = os.path.join(BASE_DIR, 'storage', 'testing')
    UPLOAD_FOLDER_CURRENT = os.path.join(BASE_DIR, 'storage', 'current')
    UPLOAD_FOLDER_HISTORY = os.path.join(BASE_DIR, 'storage', 'history')
    
    # 确保所有目录存在
    for folder in [UPLOAD_FOLDER_TESTING, UPLOAD_FOLDER_CURRENT, UPLOAD_FOLDER_HISTORY]:
        os.makedirs(folder, exist_ok=True)
    
    # 最大文件大小 (200MB)
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024
