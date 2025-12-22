# Konnect AI Android App

https://konnect-ai.net 웹앱의 Android WebView 래퍼 앱입니다.

## 요구사항

- Android Studio Hedgehog (2023.1.1) 이상
- JDK 17 이상
- Android SDK 34

## 빌드 방법

### Android Studio 사용 (권장)

1. Android Studio에서 `android` 폴더를 프로젝트로 열기
2. Gradle Sync 완료 대기
3. Build > Generate Signed Bundle / APK 선택

### 커맨드라인 빌드

```bash
# Debug APK
./gradlew assembleDebug

# Release APK (서명 필요)
./gradlew assembleRelease

# AAB (Play Store용)
./gradlew bundleRelease
```

## 서명 키 생성

Release 빌드를 위해 서명 키가 필요합니다:

```bash
keytool -genkey -v -keystore konnectai-release.jks \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -alias konnectai -storepass <비밀번호> -keypass <비밀번호>
```

### Release 서명 설정

`app/build.gradle.kts`에 추가:

```kotlin
android {
    signingConfigs {
        create("release") {
            storeFile = file("../konnectai-release.jks")
            storePassword = "<비밀번호>"
            keyAlias = "konnectai"
            keyPassword = "<비밀번호>"
        }
    }
    
    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("release")
            // ... 기존 설정
        }
    }
}
```

## 앱 배포

### AppIntos
- `app/build/outputs/apk/release/app-release.apk` 업로드

### Google Play Store
- `app/build/outputs/bundle/release/app-release.aab` 업로드
- 개발자 계정 필요 ($25 일회성)

## 앱 정보

- **Package Name**: net.konnectai.app
- **Min SDK**: 24 (Android 7.0)
- **Target SDK**: 34 (Android 14)
- **Version**: 1.0.0

## 기능

- WebView로 konnect-ai.net 로드
- Pull-to-refresh 지원
- 네트워크 오류 처리
- 외부 링크 브라우저에서 열기
- Deep linking 지원 (https://konnect-ai.net)
