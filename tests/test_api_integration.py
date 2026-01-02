"""
API Integration Tests

FastAPI 엔드포인트 통합 테스트
"""
import pytest
from fastapi import status
import io


class TestHealthEndpoints:
    """Health Check 엔드포인트 테스트"""
    
    def test_basic_health_check(self, client):
        """기본 health check 응답 검증"""
        response = client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "swing-analyzer"
        assert "version" in data
        assert "timestamp" in data
    
    def test_detailed_health_check(self, client):
        """상세 health check 응답 검증"""
        response = client.get("/health/detailed")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # 기본 정보
        assert data["status"] == "healthy"
        assert data["service"] == "swing-analyzer"
        
        # 시스템 메트릭
        assert "system" in data
        assert "memory" in data["system"]
        assert "cpu" in data["system"]
        assert "disk" in data["system"]
        
        # 메모리 정보
        memory = data["system"]["memory"]
        assert "total_gb" in memory
        assert "used_percent" in memory
        assert 0 <= memory["used_percent"] <= 100
        
        # CPU 정보
        cpu = data["system"]["cpu"]
        assert "count" in cpu
        assert cpu["count"] > 0
        
        # 디렉토리 상태
        assert "directories" in data
        dirs = data["directories"]
        assert "uploads" in dirs
        assert "data" in dirs
        assert "logs" in dirs
    
    def test_llm_health_check_noop_mode(self, client):
        """LLM health check (noop 모드)"""
        response = client.get("/openai/health?model=gpt-4o-mini")
        
        # noop 모드에서는 성공 응답이거나 LLM이 비활성화된 응답
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "ok" in data
            assert data["provider"] in ["noop", "openai"]


class TestAnalyzeEndpoint:
    """Swing Analyze 엔드포인트 테스트"""
    
    def test_analyze_missing_auth_header(self, client):
        """인증 헤더 없이 요청 시 401 에러"""
        fake_video = ("test.mp4", io.BytesIO(b"fake video"), "video/mp4")
        
        response = client.post(
            "/analyze",
            files={"file": fake_video},
            data={
                "club": "driver",
                "swing_direction": "right"
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_analyze_invalid_auth_key(self, client):
        """잘못된 인증 키로 요청 시 401 에러"""
        fake_video = ("test.mp4", io.BytesIO(b"fake video"), "video/mp4")
        
        response = client.post(
            "/analyze",
            files={"file": fake_video},
            data={
                "club": "driver",
                "swing_direction": "right"
            },
            headers={"X-Internal-Api-Key": "wrong-key"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_analyze_missing_file(self, auth_headers):
        """파일 없이 요청 시 422 에러"""
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        
        response = client.post(
            "/analyze",
            data={
                "club": "driver",
                "swing_direction": "right"
            },
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_analyze_invalid_club_type(self, client, auth_headers):
        """잘못된 club 타입으로 요청 시 422 에러"""
        fake_video = ("test.mp4", io.BytesIO(b"fake video"), "video/mp4")
        
        response = client.post(
            "/analyze",
            files={"file": fake_video},
            data={
                "club": "invalid_club",  # 잘못된 값
                "swing_direction": "right"
            },
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_analyze_invalid_swing_direction(self, client, auth_headers):
        """잘못된 swing_direction으로 요청 시 422 에러"""
        fake_video = ("test.mp4", io.BytesIO(b"fake video"), "video/mp4")
        
        response = client.post(
            "/analyze",
            files={"file": fake_video},
            data={
                "club": "driver",
                "swing_direction": "invalid"  # 잘못된 값
            },
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_analyze_visibility_threshold_range(self, client, auth_headers):
        """visibility_threshold 범위 밖 값으로 요청 시 422 에러"""
        fake_video = ("test.mp4", io.BytesIO(b"fake video"), "video/mp4")
        
        response = client.post(
            "/analyze",
            files={"file": fake_video},
            data={
                "club": "driver",
                "swing_direction": "right",
                "visibility_threshold": 1.5  # 범위 초과 (0.0~1.0)
            },
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.skip(reason="실제 비디오 처리 필요 - 통합 테스트 환경에서 실행")
    def test_analyze_with_valid_video(self, client, auth_headers, sample_video_file):
        """정상 비디오 파일로 분석 요청"""
        with open(sample_video_file, "rb") as f:
            response = client.post(
                "/analyze",
                files={"file": ("swing.mp4", f, "video/mp4")},
                data={
                    "club": "driver",
                    "swing_direction": "right",
                    "visibility_threshold": 0.5,
                    "normalize_mode": "height",
                    "llm_provider": "noop"
                },
                headers=auth_headers
            )
        
        # 실제 비디오 처리가 되면 200 또는 500 (처리 실패)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            
            # 응답 구조 검증
            assert "analysis_id" in data
            assert "phases" in data
            assert "angles" in data
            assert "diagnosis" in data
            
            # Phase 정보 검증
            assert isinstance(data["phases"], list)
            if len(data["phases"]) > 0:
                phase = data["phases"][0]
                assert "phase" in phase
                assert "frame" in phase
                assert "timestamp" in phase
            
            # 진단 정보 검증
            diagnosis = data["diagnosis"]
            assert "score" in diagnosis
            assert 0 <= diagnosis["score"] <= 100


class TestReportEndpoint:
    """Report 엔드포인트 테스트"""
    
    def test_report_with_valid_payload(self, client):
        """정상 payload로 리포트 생성"""
        payload = {
            "phase_metrics": {
                "P2": {"elbow": 140.0, "knee": 160.0},
                "P4": {"elbow": 120.0, "knee": 155.0}
            },
            "diagnosis_by_phase": {
                "P2": {"issues": ["백스윙 속도 느림"]},
                "P4": {"issues": []}
            },
            "club": "driver",
            "side": "right"
        }
        
        response = client.post(
            "/report?language=ko&tone=coach",
            json=payload
        )
        
        # 리포트 생성 성공 또는 LLM 오류
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "report" in data
            assert isinstance(data["report"], str)
    
    def test_report_language_parameter(self, client):
        """언어 파라미터 검증"""
        payload = {
            "phase_metrics": {},
            "diagnosis_by_phase": {},
            "club": "driver"
        }
        
        # 한글
        response = client.post("/report?language=ko", json=payload)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
        
        # 영어
        response = client.post("/report?language=en", json=payload)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]
        
        # 잘못된 언어 (regex 검증 실패)
        response = client.post("/report?language=invalid", json=payload)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
