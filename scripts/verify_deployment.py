#!/usr/bin/env python3
"""
배포 준비 상태 검증 스크립트

Railway 배포 전에 모든 필수 파일과 설정을 확인합니다.

사용법:
    python scripts/verify_deployment.py
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Tuple

# ANSI Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def print_header(text: str):
    """섹션 헤더 출력"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text.center(60)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_success(text: str):
    """성공 메시지 출력"""
    print(f"{GREEN}✓{RESET} {text}")

def print_error(text: str):
    """에러 메시지 출력"""
    print(f"{RED}✗{RESET} {text}")

def print_warning(text: str):
    """경고 메시지 출력"""
    print(f"{YELLOW}⚠{RESET} {text}")

def check_file_exists(filepath: str, required: bool = True) -> bool:
    """파일 존재 확인"""
    path = Path(filepath)
    if path.exists():
        print_success(f"{filepath} 존재")
        return True
    else:
        if required:
            print_error(f"{filepath} 누락 (필수)")
        else:
            print_warning(f"{filepath} 누락 (선택)")
        return not required

def check_railway_config() -> Tuple[int, int]:
    """Railway 설정 파일 확인"""
    print_header("Railway 설정 파일 확인")

    passed = 0
    failed = 0

    # Root railway.json
    if check_file_exists("railway.json"):
        try:
            with open("railway.json", "r") as f:
                config = json.load(f)
                if "build" in config and "deploy" in config:
                    print_success("  - Root railway.json 형식 정상")
                    passed += 1
                else:
                    print_error("  - Root railway.json 형식 오류")
                    failed += 1
        except json.JSONDecodeError:
            print_error("  - Root railway.json JSON 파싱 실패")
            failed += 1
    else:
        failed += 1

    # Backend railway.json
    if check_file_exists("backend/railway.json"):
        try:
            with open("backend/railway.json", "r") as f:
                config = json.load(f)
                if "build" in config and "deploy" in config:
                    print_success("  - Backend railway.json 형식 정상")
                    if "healthcheckPath" in config["deploy"]:
                        print_success("  - Health check 설정됨")
                    passed += 1
                else:
                    print_error("  - Backend railway.json 형식 오류")
                    failed += 1
        except json.JSONDecodeError:
            print_error("  - Backend railway.json JSON 파싱 실패")
            failed += 1
    else:
        failed += 1

    # Frontend railway.json
    if check_file_exists("frontend/railway.json"):
        try:
            with open("frontend/railway.json", "r") as f:
                config = json.load(f)
                if "build" in config and "deploy" in config:
                    print_success("  - Frontend railway.json 형식 정상")
                    passed += 1
                else:
                    print_error("  - Frontend railway.json 형식 오류")
                    failed += 1
        except json.JSONDecodeError:
            print_error("  - Frontend railway.json JSON 파싱 실패")
            failed += 1
    else:
        failed += 1

    # .railwayignore
    if check_file_exists(".railwayignore"):
        passed += 1
    else:
        failed += 1

    return passed, failed

def check_backend_files() -> Tuple[int, int]:
    """백엔드 필수 파일 확인"""
    print_header("백엔드 필수 파일 확인")

    passed = 0
    failed = 0

    required_files = [
        "backend/requirements.txt",
        "backend/app/main.py",
        "backend/app/database.py",
        "backend/app/core/config.py",
        "backend/scripts/db_migrate.py",
        "backend/scripts/create_admin.py",
    ]

    for filepath in required_files:
        if check_file_exists(filepath):
            passed += 1
        else:
            failed += 1

    # requirements.txt 검증
    if Path("backend/requirements.txt").exists():
        with open("backend/requirements.txt", "r") as f:
            content = f.read()
            required_packages = [
                "fastapi",
                "uvicorn",
                "sqlalchemy",
                "asyncpg",
                "redis",
                "neo4j",
                "python-jose",
                "passlib",
                "pydantic",
                "psutil",
            ]

            for package in required_packages:
                if package in content.lower():
                    print_success(f"  - {package} 패키지 포함")
                else:
                    print_error(f"  - {package} 패키지 누락")
                    failed += 1

    return passed, failed

def check_frontend_files() -> Tuple[int, int]:
    """프론트엔드 필수 파일 확인"""
    print_header("프론트엔드 필수 파일 확인")

    passed = 0
    failed = 0

    required_files = [
        "frontend/package.json",
        "frontend/vite.config.ts",
        "frontend/tsconfig.json",
        "frontend/index.html",
        "frontend/src/main.tsx",
        "frontend/src/App.tsx",
    ]

    for filepath in required_files:
        if check_file_exists(filepath):
            passed += 1
        else:
            failed += 1

    # package.json 검증
    if Path("frontend/package.json").exists():
        with open("frontend/package.json", "r") as f:
            try:
                package = json.load(f)

                # Scripts 확인
                if "scripts" in package:
                    required_scripts = ["dev", "build", "start"]
                    for script in required_scripts:
                        if script in package["scripts"]:
                            print_success(f"  - npm {script} 스크립트 존재")
                            passed += 1
                        else:
                            print_error(f"  - npm {script} 스크립트 누락")
                            failed += 1

                # Dependencies 확인
                if "dependencies" in package:
                    required_deps = ["react", "react-dom", "react-router-dom", "axios"]
                    for dep in required_deps:
                        if dep in package["dependencies"]:
                            print_success(f"  - {dep} 의존성 포함")
                        else:
                            print_error(f"  - {dep} 의존성 누락")
                            failed += 1
            except json.JSONDecodeError:
                print_error("  - package.json JSON 파싱 실패")
                failed += 1

    return passed, failed

def check_environment_template() -> Tuple[int, int]:
    """환경 변수 템플릿 확인"""
    print_header("환경 변수 템플릿 확인")

    passed = 0
    failed = 0

    # Backend .env.example
    if check_file_exists("backend/.env.example", required=False):
        with open("backend/.env.example", "r") as f:
            content = f.read()
            required_vars = [
                "DATABASE_URL",
                "REDIS_URL",
                "NEO4J_URI",
                "NEO4J_USER",
                "NEO4J_PASSWORD",
                "SECRET_KEY",
                "DART_API_KEY",
                "R2_ACCESS_KEY_ID",
                "R2_SECRET_ACCESS_KEY",
                "R2_BUCKET_NAME",
                "R2_ENDPOINT_URL",
                "ENVIRONMENT",
            ]

            for var in required_vars:
                if var in content:
                    print_success(f"  - {var} 변수 템플릿 존재")
                    passed += 1
                else:
                    print_warning(f"  - {var} 변수 템플릿 누락")
    else:
        print_warning("backend/.env.example 파일 없음 (권장)")

    # Frontend .env.example
    if check_file_exists("frontend/.env.example", required=False):
        with open("frontend/.env.example", "r") as f:
            content = f.read()
            required_vars = ["VITE_API_URL", "VITE_APP_NAME"]

            for var in required_vars:
                if var in content:
                    print_success(f"  - {var} 변수 템플릿 존재")
                    passed += 1
                else:
                    print_warning(f"  - {var} 변수 템플릿 누락")
    else:
        print_warning("frontend/.env.example 파일 없음 (권장)")

    return passed, failed

def check_documentation() -> Tuple[int, int]:
    """문서 파일 확인"""
    print_header("배포 문서 확인")

    passed = 0
    failed = 0

    required_docs = [
        "README.md",
        "DEPLOYMENT.md",
        "DEPLOYMENT_CHECKLIST.md",
        "QUICK_START.md",
        "OPERATIONS.md",
    ]

    for doc in required_docs:
        if check_file_exists(doc, required=False):
            passed += 1

    return passed, failed

def check_git_status() -> Tuple[int, int]:
    """Git 상태 확인"""
    print_header("Git 상태 확인")

    passed = 0
    failed = 0

    # .git 디렉토리 확인
    if Path(".git").exists():
        print_success("Git 저장소 초기화됨")
        passed += 1

        # .gitignore 확인
        if check_file_exists(".gitignore"):
            with open(".gitignore", "r") as f:
                content = f.read()
                required_ignores = [".env", "__pycache__", "node_modules", "dist", ".venv"]

                for ignore in required_ignores:
                    if ignore in content:
                        print_success(f"  - {ignore} .gitignore에 포함")
                        passed += 1
                    else:
                        print_warning(f"  - {ignore} .gitignore에 누락")
        else:
            print_error(".gitignore 파일 누락")
            failed += 1
    else:
        print_error("Git 저장소가 초기화되지 않음")
        failed += 1

    return passed, failed

def check_scripts_executable() -> Tuple[int, int]:
    """스크립트 실행 권한 확인"""
    print_header("배포 스크립트 확인")

    passed = 0
    failed = 0

    scripts = [
        "backend/scripts/db_migrate.py",
        "backend/scripts/create_admin.py",
        "scripts/deploy.sh",
    ]

    for script in scripts:
        if Path(script).exists():
            # Python 파일인지 확인
            if script.endswith(".py"):
                with open(script, "r") as f:
                    first_line = f.readline()
                    if first_line.startswith("#!"):
                        print_success(f"{script} - shebang 존재")
                    else:
                        print_warning(f"{script} - shebang 권장")

            # Shell 스크립트인지 확인
            if script.endswith(".sh"):
                if os.access(script, os.X_OK):
                    print_success(f"{script} - 실행 권한 있음")
                    passed += 1
                else:
                    print_warning(f"{script} - 실행 권한 없음 (chmod +x 필요)")
            else:
                passed += 1
        else:
            print_error(f"{script} 누락")
            failed += 1

    return passed, failed

def main():
    """메인 검증 함수"""
    print(f"\n{BLUE}╔══════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BLUE}║{RESET}     {'Raymontology Railway 배포 준비 상태 검증'.center(54)}     {BLUE}║{RESET}")
    print(f"{BLUE}╚══════════════════════════════════════════════════════════╝{RESET}\n")

    total_passed = 0
    total_failed = 0

    # 모든 검증 실행
    checks = [
        check_railway_config,
        check_backend_files,
        check_frontend_files,
        check_environment_template,
        check_documentation,
        check_git_status,
        check_scripts_executable,
    ]

    for check_func in checks:
        passed, failed = check_func()
        total_passed += passed
        total_failed += failed

    # 최종 결과
    print_header("검증 결과 요약")
    print(f"  통과: {GREEN}{total_passed}{RESET}")
    print(f"  실패: {RED}{total_failed}{RESET}")
    print(f"  총계: {total_passed + total_failed}")

    success_rate = (total_passed / (total_passed + total_failed) * 100) if (total_passed + total_failed) > 0 else 0
    print(f"  성공률: {GREEN if success_rate >= 90 else YELLOW if success_rate >= 70 else RED}{success_rate:.1f}%{RESET}")

    # 배포 가능 여부 판단
    print("\n" + "="*60)
    if total_failed == 0:
        print(f"{GREEN}✓ 배포 준비 완료! Railway 배포를 진행할 수 있습니다.{RESET}")
        print(f"\n다음 단계:")
        print(f"  1. git push origin main")
        print(f"  2. Railway 대시보드에서 배포 확인")
        print(f"  3. railway run python backend/scripts/db_migrate.py create")
        print(f"  4. railway run python backend/scripts/create_admin.py")
        print("\n자세한 가이드: DEPLOYMENT_CHECKLIST.md")
        return 0
    elif total_failed <= 5:
        print(f"{YELLOW}⚠ 일부 문제가 있지만 배포 가능합니다.{RESET}")
        print(f"  위의 {RED}✗{RESET} 표시된 항목을 확인하고 수정하세요.")
        return 1
    else:
        print(f"{RED}✗ 배포 전에 문제를 해결해야 합니다.{RESET}")
        print(f"  {RED}{total_failed}개{RESET}의 필수 항목이 누락되었습니다.")
        print(f"\n문서 참고:")
        print(f"  - DEPLOYMENT.md - 상세 배포 가이드")
        print(f"  - QUICK_START.md - 빠른 시작 가이드")
        return 2

if __name__ == "__main__":
    sys.exit(main())
