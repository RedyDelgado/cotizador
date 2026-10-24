<?php

use Illuminate\Support\Facades\Schedule;

// Con "php artisan schedule:work" (o un cron por minuto con "schedule:run") corre solo.
Schedule::command('telegram:poll --once')->everyMinute()->withoutOverlapping();
Schedule::command('billing:reminders')->dailyAt('09:00');
