package com.aivideotool.app.data

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

interface AuthApi {
    @POST("auth/login")
    suspend fun login(@Body body: LoginRequest): TokenResponse

    @POST("auth/register")
    suspend fun register(@Body body: RegisterRequest): TokenResponse
}

interface TaskApi {
    @GET("history")
    suspend fun listTasks(): List<TaskDto>
}
