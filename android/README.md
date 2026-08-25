# Android 客户端

原生 Kotlin + Jetpack Compose 客户端，当前已实现登录与任务中心基础功能。

## 技术栈

- Kotlin 2.0
- Jetpack Compose + Material 3
- Retrofit + OkHttp
- Navigation Compose
- minSdk 26 / targetSdk 35

## 目录

```text
android/
├── app/
│   ├── build.gradle.kts
│   └── src/main/
│       ├── AndroidManifest.xml
│       ├── java/com/aivideotool/app/
│       │   ├── MainActivity.kt
│       │   ├── data/          # TokenManager / ApiClient / Models
│       │   └── ui/            # LoginScreen / TaskListScreen
│       └── res/values/
├── build.gradle.kts
├── settings.gradle.kts
└── gradle.properties
```

## 构建

需要 Android Studio / Android SDK 35。

```bash
cd android
# 首次使用 Android Studio 打开后会自动生成 Gradle Wrapper
./gradlew assembleDebug
```

## 后续开发

- [x] 登录 / 注册 / Token 管理
- [x] 任务列表（任务中心）
- [ ] 创建任务（文生视频 / 图生视频）
- [ ] 角色库
- [ ] 模板市场
- [ ] 3D 白模编辑器（Filament）
- [ ] 视频预览与下载
- [ ] 成本中心
