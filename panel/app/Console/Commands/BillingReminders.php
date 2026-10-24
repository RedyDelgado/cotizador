<?php

namespace App\Console\Commands;

use App\Models\Subscriber;
use App\Services\Telegram;
use Illuminate\Console\Command;

class BillingReminders extends Command
{
    protected $signature = 'billing:reminders';

    protected $description = 'Avisa por Telegram a quien está por vencer (3 días antes) o ya venció (al día siguiente)';

    public function handle(Telegram $telegram): int
    {
        $price = config('panel.currency').' '.number_format(config('panel.price'), 2).' por '.config('panel.days').' días';
        $sent = 0;

        Subscriber::active()->whereNotNull('paid_until')->whereNotNull('telegram_chat_id')->each(function (Subscriber $s) use ($telegram, $price, &$sent) {
            $left = $s->daysLeft();
            $stage = match (true) {
                $left === config('panel.expiring_days') => 'before',
                $left === -1 => 'after',
                default => null,
            };
            $mark = $s->paid_until->toDateString().':'.$stage;
            if ($stage === null || $s->last_reminder === $mark) {
                return;
            }
            $text = $stage === 'before'
                ? "Tu servicio de NEOESTADO vence en {$left} días (".$s->paid_until->format('d/m/Y')."). Para renovar: {$price}."
                : 'Tu servicio de NEOESTADO venció ayer y dejaste de recibir el resumen. '."Para reactivarlo: {$price}.";
            if ($telegram->send($s->telegram_chat_id, $text)) {
                $s->update(['last_reminder' => $mark]);
                $sent++;
            }
        });

        $this->info("{$sent} avisos enviados.");

        return self::SUCCESS;
    }
}
