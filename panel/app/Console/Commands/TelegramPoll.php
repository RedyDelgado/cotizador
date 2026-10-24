<?php

namespace App\Console\Commands;

use App\Models\Subscriber;
use App\Services\Telegram;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Cache;

class TelegramPoll extends Command
{
    protected $signature = 'telegram:poll {--once : Revisa una vez y termina (para programarlo cada minuto)}';

    protected $description = 'Atiende los mensajes del bot de Telegram: vincula al suscriptor que abre su enlace (/start CÓDIGO)';

    public function handle(Telegram $telegram): int
    {
        if (! $telegram->configured()) {
            $this->warn('Falta TELEGRAM_BOT_TOKEN: no hay nada que atender.');

            return self::SUCCESS;
        }
        do {
            $offset = (int) Cache::get('telegram_offset', 0);
            foreach ($telegram->updates($offset, $this->option('once') ? 0 : 25) as $update) {
                $offset = max($offset, $update['update_id'] + 1);
                $this->handleMessage($telegram, $update['message'] ?? []);
            }
            Cache::forever('telegram_offset', $offset);
        } while (! $this->option('once'));

        return self::SUCCESS;
    }

    /** @param  array<string, mixed>  $message */
    private function handleMessage(Telegram $telegram, array $message): void
    {
        $chatId = $message['chat']['id'] ?? null;
        $text = trim((string) ($message['text'] ?? ''));
        if (! $chatId || $text === '') {
            return;
        }

        if (preg_match('/^\/start\s+([A-Za-z0-9]{4,16})$/', $text, $m)) {
            $subscriber = Subscriber::where('telegram_link_code', strtoupper($m[1]))->first();
            if (! $subscriber) {
                $telegram->send($chatId, 'Ese enlace no es válido. Pide uno nuevo a quien administra tu suscripción.');

                return;
            }
            $subscriber->update(['telegram_chat_id' => (string) $chatId]);
            $telegram->send($chatId, '<b>Listo, '.e($subscriber->name).'.</b> Recibirás aquí el resumen diario de oportunidades de NEOESTADO. '
                .'Escribe /estado para ver hasta cuándo tienes el servicio.');

            return;
        }

        if ($text === '/estado') {
            $subscriber = Subscriber::where('telegram_chat_id', (string) $chatId)->first();
            $telegram->send($chatId, $subscriber ? $this->statusText($subscriber) : 'Aún no estás vinculado. Abre el enlace que te dieron.');

            return;
        }

        $telegram->send($chatId, 'Hola. Para vincular tu cuenta abre el enlace personal que te enviaron. Comandos: /estado');
    }

    private function statusText(Subscriber $subscriber): string
    {
        $left = $subscriber->daysLeft();
        $price = config('panel.currency').' '.number_format(config('panel.price'), 2).' por '.config('panel.days').' días';

        return match (true) {
            $left === null => "Aún no tienes un pago registrado. Renueva: {$price}.",
            $left < 0 => 'Tu servicio venció el '.$subscriber->paid_until->format('d/m/Y').". Renueva: {$price}.",
            default => 'Tu servicio está vigente hasta el '.$subscriber->paid_until->format('d/m/Y')." (quedan {$left} días).",
        };
    }
}
