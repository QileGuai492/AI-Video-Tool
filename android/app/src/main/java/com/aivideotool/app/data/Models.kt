package com.aivideotool.app.data

import com.google.gson.annotations.SerializedName

data class LoginRequest(
    val username: String,
    val password: String,
)

data class RegisterRequest(
    val username: String,
    val password: String,
    val email: String? = null,
)

data class TokenResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String = "bearer",
    @SerializedName("expires_in") val expiresIn: Int = 0,
)

data class TaskDto(
    val id: Int,
    val uid: String,
    val prompt: String,
    val status: String,
    @SerializedName("video_url") val videoUrl: String? = null,
    @SerializedName("audio_url") val audioUrl: String? = null,
    @SerializedName("subtitle_url") val subtitleUrl: String? = null,
    val duration: Int? = null,
    @SerializedName("aspect_ratio") val aspectRatio: String? = null,
    @SerializedName("created_at") val createdAt: String? = null,
)
