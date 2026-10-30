plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }
android {
    namespace = "com.gametodo.nativeapp"
    compileSdk = 35
    defaultConfig {
        applicationId = "com.gametodo.cipherlink"
        minSdk = 30
        targetSdk = 35
        versionCode = 38
        versionName = "0.11.10"
        // New signing lineage; old installations and their Keystore remain intact.
        resValue("string", "app_name", "사이퍼링크")
    }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    kotlinOptions { jvmTarget = "17" }
}
dependencies {
    // 앱을 종료해도 주기 동기화 예약 유지. 안드로이드 배터리 제한을 준수한다.
    implementation("androidx.work:work-runtime:2.10.2")
    implementation("org.jsoup:jsoup:1.18.3")
}
