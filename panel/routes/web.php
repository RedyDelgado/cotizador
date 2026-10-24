<?php

use App\Http\Controllers\AuthController;
use App\Http\Controllers\PaymentController;
use App\Http\Controllers\SubscriberController;
use Illuminate\Support\Facades\Route;

Route::middleware('guest')->group(function () {
    Route::get('/login', [AuthController::class, 'showLogin'])->name('login');
    Route::post('/login', [AuthController::class, 'login'])->middleware('throttle:10,1');
});

Route::middleware('auth')->group(function () {
    Route::redirect('/', '/subscribers');
    Route::post('/logout', [AuthController::class, 'logout'])->name('logout');
    Route::resource('subscribers', SubscriberController::class)->except('show');
    Route::get('/subscribers/{subscriber}/payments', [PaymentController::class, 'index'])->name('subscribers.payments.index');
    Route::post('/subscribers/{subscriber}/payments', [PaymentController::class, 'store'])->name('subscribers.payments.store');
    Route::patch('/subscribers/{subscriber}/toggle', [SubscriberController::class, 'toggle'])->name('subscribers.toggle');
});
