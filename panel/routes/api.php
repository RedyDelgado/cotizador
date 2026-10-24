<?php

use App\Http\Controllers\Api\BotController;
use App\Http\Controllers\Api\SubscriberController;
use Illuminate\Support\Facades\Route;

// Administración: token con la habilidad "subscribers" (php artisan panel:token NOMBRE --abilities=subscribers).
Route::middleware(['auth:sanctum', 'abilities:subscribers', 'throttle:120,1'])->group(function () {
    Route::apiResource('subscribers', SubscriberController::class)->names('api.subscribers');
    Route::patch('subscribers/{subscriber}/pause', [SubscriberController::class, 'pause']);
});

// Bot de Python: token con la habilidad "bot" (solo lee los perfiles activos y avisa lo que envió).
Route::prefix('bot')->middleware(['auth:sanctum', 'abilities:bot', 'throttle:60,1'])->group(function () {
    Route::get('profiles', [BotController::class, 'profiles']);
    Route::post('sent', [BotController::class, 'sent']);
});
