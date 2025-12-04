from datetime import datetime
from typing import Optional

import boto3

from app.schemas.analyze_dto import AnalyzeSwingResponse


class S3StorageClient:
    """AWS S3에 분석 결과 저장"""

    def __init__(
        self,
        bucket_name: str,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1"
    ):
        """
        Args:
            bucket_name: S3 버킷 이름
            aws_access_key_id: AWS Access Key (None이면 환경변수/IAM Role 사용)
            aws_secret_access_key: AWS Secret Key
            region_name: AWS 리전
        """
        self.bucket_name = bucket_name

        if aws_access_key_id and aws_secret_access_key:
            self.s3_client = boto3.client(
                "s3",
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region_name
            )
        else:
            # 환경변수나 IAM Role 사용
            self.s3_client = boto3.client("s3", region_name=region_name)

    def upload_result(self, result: AnalyzeSwingResponse) -> str:
        """
        분석 결과를 S3에 JSON으로 저장

        Args:
            result: 분석 응답 DTO

        Returns:
            S3 URL (https://bucket.s3.amazonaws.com/path/to/file.json)
        """
        # 파일명 생성 (user_id/YYYYMMDD/analysis_id.json)
        timestamp = datetime.now().strftime("%Y%m%d")
        s3_key = f"swing-analysis/{result.user_id}/{timestamp}/{result.analysis_id}.json"

        # JSON 직렬화
        json_data = result.model_dump_json(indent=2)

        # S3 업로드
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=json_data.encode("utf-8"),
            ContentType="application/json",
            Metadata={
                "user_id": result.user_id,
                "club": result.club,
                "overall_score": str(result.overall_score)
            }
        )

        # URL 생성
        url = f"https://{self.bucket_name}.s3.amazonaws.com/{s3_key}"
        return url
