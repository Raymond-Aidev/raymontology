# Raymontology Android App

기업 관계 네트워크 분석 서비스의 Android WebView 앱입니다.

## 요구사항

- Android Studio Hedgehog (2023.1.1) 이상
- JDK 17
- Android SDK 34
- Gradle 8.2

## 개발 환경 설정

### 1. Android Studio에서 프로젝트 열기

```bash
cd android
```

Android Studio > File > Open > `android` 폴더 선택

### 2. 디버그 빌드

```bash
./gradlew assembleDebug
```

APK 위치: `app/build/outputs/apk/debug/app-debug.apk`

### 3. 에뮬레이터에서 실행

1. Android Studio에서 AVD Manager 실행
2. API 24 이상 에뮬레이터 생성
3. Run 버튼 클릭

## 릴리스 빌드

### 1. 서명 키 생성

```bash
keytool -genkey -v -keystore keystore/raymontology.jks \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -alias raymontology \
  -dname "CN=Raymontology, OU=Development, O=Raymontology, L=Seoul, ST=Seoul, C=KR"
```

### 2. local.properties 설정

```properties
# android/local.properties
KEYSTORE_FILE=keystore/raymontology.jks
KEYSTORE_PASSWORD=your_keystore_password
KEY_ALIAS=raymontology
KEY_PASSWORD=your_key_password
```

### 3. build.gradle.kts 서명 설정 활성화

`app/build.gradle.kts` 파일에서 signingConfigs 주석 해제

### 4. 릴리스 빌드 실행

```bash
# APK (AppIntos 등)
./gradlew assembleRelease

# AAB (Google Play Store)
./gradlew bundleRelease
```

빌드 결과:
- APK: `app/build/outputs/apk/release/app-release.apk`
- AAB: `app/build/outputs/bundle/release/app-release.aab`

## 프로젝트 구조

```
android/
├── app/
│   ├── src/main/
│   │   ├── java/com/raymontology/app/
│   │   │   └── MainActivity.kt          # 메인 WebView 액티비티
│   │   ├── res/
│   │   │   ├── layout/activity_main.xml # 레이아웃
│   │   │   ├── values/                  # 문자열, 색상, 테마
│   │   │   └── mipmap-*/                # 앱 아이콘
│   │   └── AndroidManifest.xml
│   ├── build.gradle.kts
│   └── proguard-rules.pro
├── build.gradle.kts
├── settings.gradle.kts
└── gradle.properties
```

## 설정 변경

### WebApp URL 변경

`app/build.gradle.kts` 파일에서:

```kotlin
buildConfigField("String", "WEBAPP_URL", "\"https://your-domain.com\"")
```

### 패키지명 변경

1. `app/build.gradle.kts`의 `applicationId` 변경
2. `AndroidManifest.xml`의 `package` 변경
3. Java/Kotlin 패키지 디렉토리 이동

## 앱 스토어 제출

### AppIntos

1. `./gradlew assembleRelease`로 APK 생성
2. APK 파일 업로드
3. 앱 정보 입력:
   - 앱 이름: Raymontology
   - 카테고리: 금융/비즈니스
   - 설명, 스크린샷 등

### Google Play Store

1. `./gradlew bundleRelease`로 AAB 생성
2. Google Play Console에서 앱 등록
3. 내부 테스트 트랙에 AAB 업로드
4. 스토어 정보 입력:
   - 앱 이름: Raymontology - 기업 관계 네트워크 분석
   - 카테고리: 금융
   - 스크린샷, Feature Graphic
5. 데이터 안전 양식 작성
6. 콘텐츠 등급 설정
7. 프로덕션 출시

## 필요 자산

| 자산 | 규격 | 용도 |
|------|------|------|
| 앱 아이콘 | 512x512 PNG | 스토어/런처 |
| Feature Graphic | 1024x500 PNG | Play Store |
| 스크린샷 (폰) | 1080x1920 (2-8장) | 스토어 |
| 스크린샷 (태블릿) | 1800x2560 (선택) | 스토어 |

## 문제 해결

### WebView 로딩 안됨

1. 인터넷 권한 확인 (AndroidManifest.xml)
2. URL이 HTTPS인지 확인
3. 디버그 빌드에서 `chrome://inspect`로 WebView 디버깅

### 빌드 실패

```bash
# Gradle 캐시 클리어
./gradlew clean
rm -rf ~/.gradle/caches/

# 재빌드
./gradlew assembleDebug
```
