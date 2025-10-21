# =============================================================================
# Makefile — swing-analyzer (자주 쓰는 것 위, 가끔 쓰는 것 아래)
#
# 가장 많이 쓰는 흐름:
#   1) make release BY=phase KEEP=5 AUTO_COMMIT=1
#      - 최신 thresholds 생성(phase/club/overall 선택 가능)
#      - thresholds_current.json 심링크 갱신
#      - 오래된 버전 자동 보관(data/thresholds/archive)
#      - Git에 current + 최신 날짜 파일만 stage (AUTO_COMMIT=1이면 자동 커밋)
#
# 그 다음 자주 쓰는 것:
#   2) make dataset            # logs → data/datasets/phase_dataset.csv 재생성
#   3) make api                # 로컬 API 서버 실행
#   4) make analyze-sample     # sample mp4로 /analyze 호출 (서버 먼저 띄워야 함)
#
# 테스트/디버그용(가끔 사용):
#   5) make thresholds.phase   # TEST_thresholds.json 생성(커밋 대상 아님)
#      make thresholds.club
#      make thresholds.overall
#
# 유지보수/정리(필요할 때):
#   6) make logs-clean         # data/logs/*.json 비우기
#      make clean              # 캐시/임시 산출물 정리
#      make fmt / make lint    # 코드 포맷/린트 (선택)
# =============================================================================

# ====== 공통 변수 (CLI에서 override 가능: 예) make release BY=club KEEP=3) ======
PY        ?= python            # 파이썬 실행기
APP       ?= app.main:app      # uvicorn 엔트리포인트 (FastAPI)
HOST      ?= 127.0.0.1
PORT      ?= 8000

CSV       ?= data/datasets/phase_dataset.csv   # thresholds 입력 CSV
OUTDIR    ?= app/config                        # thresholds 산출 폴더
NAMEFMT   ?= {date}_thresholds.json            # rotate 시 날짜 파일 패턴
BY        ?= phase                             # phase | club | overall
KEEP      ?= 5                                 # current 제외, 보관할 날짜 파일 개수
AUTO_COMMIT ?= 0                               # 1이면 release 시 자동 커밋

SAMPLE_MP4 ?= uploads/sample.mp4               # analyze-sample 입력 파일
CLUB       ?= iron
SIDE       ?= right

# ====== 타겟 선언 ======
.PHONY: help release rotate dataset api analyze-sample \
        thresholds thresholds.phase thresholds.club thresholds.overall \
        fmt lint clean logs-clean show-env

# -----------------------------------------------------------------------------
# [가장 자주 쓰는 타겟]
# -----------------------------------------------------------------------------

# release:
# - 실사용 파이프라인 (추천)
# - rotate(버전 생성 + current 갱신 + 보관정책) + Git stage (+ 자동커밋 옵션)
# - 일반적인 배포/반영 사이클일 때 이거 하나로 끝냄
release: rotate
	@echo "[release] stage thresholds_current.json + latest dated json"
	@latest_file=$$(ls -1t $(OUTDIR)/*_thresholds.json 2>/dev/null | grep -v 'thresholds_current.json' | head -n1); \
	if [ -z "$$latest_file" ]; then \
	  echo "[release] no dated thresholds found"; exit 1; \
	fi; \
	git add $(OUTDIR)/thresholds_current.json "$$latest_file"; \
	echo "[release] staged: thresholds_current.json and $$latest_file"; \
	if [ "$(AUTO_COMMIT)" = "1" ]; then \
	  msg=$$(basename "$$latest_file"); \
	  git commit -m "release(thresholds): set current -> $${msg} [by=$(BY)]" || true; \
	  echo "[release] committed."; \
	else \
	  echo "[release] (dry) staged only. Set AUTO_COMMIT=1 to auto-commit."; \
	fi

# rotate:
# - thresholds를 “운영용”으로 새로 뽑고, current 심링크 갱신
# - KEEP 정책에 따라 오래된 파일은 data/thresholds/archive로 이동
# - Git 반영은 하지 않음(= release에서 stage/commit)
rotate:
	@echo "[rotate] build $(BY) thresholds -> $(OUTDIR)/{date}_thresholds.json"
	$(PY) -m scripts.thresholds.rotate_thresholds \
	  --csv $(CSV) \
	  --by $(BY) \
	  --outdir $(OUTDIR) \
	  --namefmt "$(NAMEFMT)"

	@echo "[rotate] retention: keep latest $(KEEP) *_thresholds.json (excluding current), older -> data/thresholds/archive"
	@mkdir -p data/thresholds/archive
	@touch data/thresholds/archive/.keep
	@ls -1t $(OUTDIR)/*_thresholds.json 2>/dev/null | \
	  grep -v 'thresholds_current.json' | \
	  awk 'NR>$(KEEP)' | \
	  xargs -I{} sh -c 'mv "$$1" data/thresholds/archive/ || true' sh {}

# dataset:
# - data/logs/*.json → data/datasets/phase_dataset.csv 재생성
# - thresholds를 갱신하기 전에 최신 로그 기반으로 CSV를 다시 만들 때 사용
dataset:
	$(PY) -m scripts.datasets.build_phase_dataset

# api:
# - 로컬 개발 서버 실행 (FastAPI + uvicorn)
# - 프론트/클라이언트/테스트와 연동해서 결과 확인할 때 사용
api:
	$(PY) -m uvicorn $(APP) --host $(HOST) --port $(PORT) --reload

# analyze-sample:
# - 서버가 떠 있는 상태에서 샘플 mp4를 /analyze로 보내 결과를 JSON으로 확인
# - API 응답 형태/값 빠르게 점검할 때 사용
analyze-sample:
	@echo "POST /analyze -> $(SAMPLE_MP4)"
	@curl -s -X POST "http://$(HOST):$(PORT)/analyze" \
	  -F "file=@$(SAMPLE_MP4)" \
	  -F "side=$(SIDE)" \
	  -F "club=$(CLUB)" | python -m json.tool

# -----------------------------------------------------------------------------
# [테스트/디버그용: TEST_* 산출물 생성 (커밋 X)]
# -----------------------------------------------------------------------------

# thresholds.*:
# - csv_to_thresholds를 바로 실행해 TEST_* 파일을 생성
# - 산출물 모양/통계 sanity-check 용도 (운영 반영은 release/rotate로)
thresholds.phase:
	$(PY) -m scripts.thresholds.csv_to_thresholds \
	  --csv $(CSV) \
	  --out $(OUTDIR)/TEST_thresholds.json \
	  --by phase

thresholds.club:
	$(PY) -m scripts.thresholds.csv_to_thresholds \
	  --csv $(CSV) \
	  --out $(OUTDIR)/TEST_thresholds_club.json \
	  --by club

thresholds.overall:
	$(PY) -m scripts.thresholds.csv_to_thresholds \
	  --csv $(CSV) \
	  --out $(OUTDIR)/TEST_thresholds_overall.json \
	  --by overall

# 3개 한 번에
thresholds: thresholds.phase thresholds.club thresholds.overall

# -----------------------------------------------------------------------------
# [유지보수/정리/품질]
# -----------------------------------------------------------------------------

# fmt:
# - 코드 자동 포맷 (ruff + black, 설치되어 있으면 동작)
fmt:
	-ruff format .
	-black .

# lint:
# - 코드 정적 분석 (ruff). 규칙에 맞는지 빠르게 확인
lint:
	-ruff check .

# clean:
# - 캐시/임시 산출물/임시 디렉토리 정리
clean:
	@echo "Cleaning caches & temp outputs..."
	@find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	@rm -rf .pytest_cache .ruff_cache
	@rm -rf data/normalized/* data/downloads/*

# logs-clean:
# - data/logs 아래 json 로그 전부 제거 (데이터셋을 새로 구성하고 싶을 때)
logs-clean:
	@rm -f data/logs/*.json || true

# show-env:
# - 현재 Make 변수들을 프린트 (디버그용)
show-env:
	@echo "PY=$(PY)"
	@echo "CSV=$(CSV)"
	@echo "OUTDIR=$(OUTDIR)"
	@echo "NAMEFMT=$(NAMEFMT)"
	@echo "BY=$(BY)"
	@echo "KEEP=$(KEEP)"
	@echo "APP=$(APP)"
	@echo "HOST=$(HOST)"
	@echo "PORT=$(PORT)"
	@echo "AUTO_COMMIT=$(AUTO_COMMIT)"

# -----------------------------------------------------------------------------
# [헬프]
# -----------------------------------------------------------------------------
help:
	@echo "Usage / Most common targets (TOP → frequently used):"
	@echo "  make release BY=phase KEEP=5 AUTO_COMMIT=1   # 실사용: 버전 생성+current 갱신+보관+Git 반영(옵션)"
	@echo "  make rotate BY=phase KEEP=5                  # 운영 버전만 생성/보관 (Git 반영 없음)"
	@echo "  make dataset                                 # logs -> data/datasets/phase_dataset.csv"
	@echo "  make api                                     # uvicorn 개발 서버"
	@echo "  make analyze-sample                          # 샘플 mp4로 /analyze 호출"
	@echo ""
	@echo "Debug / one-off:"
	@echo "  make thresholds.phase / .club / .overall     # TEST_* thresholds 생성(커밋 X)"
	@echo ""
	@echo "Maintenance:"
	@echo "  make fmt | make lint                         # 포맷/린트"
	@echo "  make clean | make logs-clean                 # 정리"
	@echo "  make show-env                                # 현재 변수 확인"