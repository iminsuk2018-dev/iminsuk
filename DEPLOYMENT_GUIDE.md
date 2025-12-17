# 🚀 Render 배포 가이드 (완전 초보용)

## 1단계: GitHub에 코드 올리기

### 1-1. GitHub 저장소 만들기

1. **GitHub 접속**: https://github.com 로그인
2. **새 저장소 만들기**:
   - 오른쪽 상단 "+" 버튼 클릭
   - "New repository" 선택
3. **저장소 정보 입력**:
   - Repository name: `pdf-research-app`
   - Description: `학술 논문 추천 시스템`
   - Public 선택 (또는 Private)
   - **아무것도 체크하지 마세요** (README, .gitignore 등)
4. **"Create repository"** 클릭

### 1-2. 로컬에서 Git 설정 (처음 한 번만)

터미널(cmd 또는 PowerShell)에서:

```bash
# Git 사용자 정보 설정 (처음 한 번만)
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### 1-3. 코드 푸시하기

```bash
# 1. pdf_research_app 폴더로 이동
cd C:\Users\user\Desktop\pdf_research_app

# 2. Git 초기화
git init

# 3. 모든 파일 추가
git add .

# 4. 첫 커밋
git commit -m "Initial commit: 학술 논문 추천 시스템"

# 5. 기본 브랜치를 main으로 설정
git branch -M main

# 6. GitHub 저장소 연결 (YOUR_USERNAME을 본인 GitHub 아이디로 변경!)
git remote add origin https://github.com/YOUR_USERNAME/pdf-research-app.git

# 7. 푸시!
git push -u origin main
```

**주의**: 6번에서 `YOUR_USERNAME`을 본인의 GitHub 아이디로 바꾸세요!

예: `git remote add origin https://github.com/minsuklim/pdf-research-app.git`

**GitHub 비밀번호 입력 시**: Personal Access Token이 필요합니다
- Settings → Developer settings → Personal access tokens → Generate new token
- repo 권한 체크 후 생성
- 생성된 토큰을 비밀번호 대신 입력

---

## 2단계: Render 배포

### 2-1. Render 계정 만들기

1. **Render 접속**: https://render.com
2. **GitHub로 가입**:
   - "Get Started for Free" 클릭
   - "Sign up with GitHub" 선택
   - GitHub 계정으로 로그인 및 권한 허용

### 2-2. 새 웹 서비스 만들기

1. **대시보드에서**:
   - 좌측 상단 "New +" 버튼 클릭
   - "Web Service" 선택

2. **저장소 연결**:
   - "Build and deploy from a Git repository" 선택
   - "Next" 클릭
   - GitHub 계정에서 `pdf-research-app` 저장소 찾기
   - "Connect" 클릭

3. **서비스 설정**:
   - **Name**: `pdf-research-app` (또는 원하는 이름)
   - **Region**: Oregon (US West) - 가장 가까운 지역
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements-web.txt`
   - **Start Command**: `gunicorn --chdir web --bind 0.0.0.0:$PORT app:app`

4. **플랜 선택**:
   - **Free** 플랜 선택 (0달러)
   - 참고: 15분 동안 활동이 없으면 슬립 모드로 전환됨

5. **"Create Web Service"** 클릭!

### 2-3. 배포 진행 상황 확인

- 자동으로 배포가 시작됩니다
- "Logs" 탭에서 실시간 진행 상황 확인
- 약 3-5분 후 배포 완료

### 2-4. 웹사이트 확인

배포 완료되면:
- 상단에 녹색 "Live" 표시
- URL: `https://pdf-research-app-xxxx.onrender.com` 형태
- URL을 클릭하면 사이트 접속!

---

## 3단계: 논문 데이터 넣기

배포된 사이트는 비어있습니다. 논문 데이터를 채워야 합니다.

### 방법 1: 로컬 데이터 업로드 (권장)

1. **로컬에서 논문 수집**:
```bash
cd C:\Users\user\Desktop\pdf_research_app
python fetch_recommendations.py
```

2. **데이터베이스 복사**:
- Render 대시보드 → Shell 탭 클릭
- 다음 명령어 실행:
```bash
mkdir -p workspace/database
# 그 다음 로컬의 workspace/database/main.db를 업로드
```

### 방법 2: Render Shell에서 직접 수집

1. Render 대시보드 → Shell 탭 클릭
2. 다음 명령어 실행:
```bash
python fetch_recommendations.py
```
(약 2-3분 소요)

---

## ✅ 완료!

이제 다음 URL에서 누구나 접속 가능합니다:
`https://your-app-name.onrender.com`

### 주의사항

1. **Free 플랜 제한**:
   - 15분 동안 활동 없으면 슬립 모드
   - 처음 접속 시 30초 정도 로딩 시간
   - 월 750시간 무료 (약 31일)

2. **데이터 업데이트**:
   - 새 논문을 추가하려면 Shell에서 `python fetch_recommendations.py` 실행
   - 또는 GitHub에 코드 변경 후 푸시하면 자동 재배포

3. **도메인 커스터마이징**:
   - Settings → Custom Domain에서 본인 도메인 연결 가능

---

## 🆘 문제 해결

### "Build failed" 오류
- Logs 탭에서 오류 메시지 확인
- 대부분 requirements-web.txt의 패키지 버전 문제

### 사이트가 안 열려요
- 배포가 완료되었는지 확인 (녹색 "Live" 표시)
- Free 플랜은 첫 접속 시 30초 정도 걸림

### 논문이 안 보여요
- Shell에서 `python fetch_recommendations.py` 실행 안 했을 수 있음
- 또는 데이터베이스가 비어있음

---

## 📞 도움말

문제가 생기면:
1. Render 대시보드 → Logs 탭에서 오류 확인
2. Shell 탭에서 명령어 직접 실행해보기
3. GitHub 저장소 → Issues에 질문 남기기
