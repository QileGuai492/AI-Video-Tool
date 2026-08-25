# Android 客户端

原生 Kotlin + Jetpack Compose 客户端，当前已实现登录/注册、任务中心基础功能，并支持在 App 内配置服务器地址（不依赖 cpolar）。

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

## 服务器地址

- 默认地址：`http://10.0.2.2:8080/api/v1/`（Android 模拟器访问宿主机）。
- 真机请改为电脑局域网 IP，例如：`http://192.168.1.100:8080/api/v1/`。
- 可在登录页点击“服务器设置”直接修改，保存后自动重试。
- 不再依赖 cpolar；cpolar 只留给外部 AI 拉取 `/uploads/` 文件。

## 后续开发

- [x] 登录 / 注册 / Token 管理
- [x] 任务列表（任务中心）
- [ ] 创建任务（文生视频 / 图生视频）
- [ ] 角色库
- [ ] 模板市场
- [ ] 3D 白模编辑器（Filament）
- [ ] 视频预览与下载
- [ ] 成本中心
