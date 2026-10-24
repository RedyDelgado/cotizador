<?php

return [
    // Suscripción: precio y duración de cada pago
    'price' => (float) env('PANEL_PRICE', 5.00),
    'days' => (int) env('PANEL_DAYS', 15),
    'currency' => env('PANEL_CURRENCY', 'S/'),
    'expiring_days' => 3, // "por vencer" y aviso previo

    // Telegram (BotFather): token y nombre de usuario del bot (sin @)
    'telegram' => [
        'token' => env('TELEGRAM_BOT_TOKEN'),
        'username' => env('TELEGRAM_BOT_USERNAME'),
        'api' => env('TELEGRAM_API_URL', 'https://api.telegram.org'),
    ],

    'payment_methods' => ['yape' => 'Yape', 'plin' => 'Plin', 'transferencia' => 'Transferencia', 'efectivo' => 'Efectivo', 'otro' => 'Otro'],
];
