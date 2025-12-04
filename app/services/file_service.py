import os
import uuid
from datetime import datetime
from fastapi import UploadFile
from app.config.settings import settings


class FileService:
    """파일 업로드 처리 서비스"""

    def __init__(self):
        self.upload_dir = settings.UPLOADS_DIR
        os.makedirs(self.upload_dir, exist_ok=True)

    async def save_uploaded_file(self, file: UploadFile) -> str:
        """
        업로드된 파일 저장

        Args:
            file: FastAPI UploadFile 객체

        Returns:
            저장된 파일의 절대 경로
        """
        # 파일명 생성 (타임스탬프 + UUID + 원본 파일명)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{timestamp}_{unique_id}_{file.filename}"
        filepath = os.path.join(self.upload_dir, filename)

        # 파일 저장
        with open(filepath, "wb") as f:
            content = await file.read()
            f.write(content)

        return filepath

    def delete_file(self, filepath: str) -> bool:
        """
        파일 삭제

        Args:
            filepath: 삭제할 파일 경로

        Returns:
            삭제 성공 여부
        """
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
        except Exception as e:
            print(f"[WARNING] File delete failed: {e}")
        return False