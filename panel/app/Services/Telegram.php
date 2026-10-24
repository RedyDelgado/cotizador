<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;

/** Cliente mínimo de la API de bots de Telegram (getUpdates y sendMessage). */
class Telegram
{
    public function configured(): bool
    {
        return (bool) config('panel.telegram.token');
    }

    /** Enlace que el suscriptor abre para vincular su Telegram: t.me/<bot>?start=<código>. */
    public function linkFor(string $code): ?string
    {
        $username = config('panel.telegram.username');

        return $username ? "https://t.me/{$username}?start={$code}" : null;
    }

    public function send(string|int $chatId, string $text): bool
    {
        if (! $this->configured()) {
            return false;
        }
        $response = Http::timeout(15)->post($this->url('sendMessage'), [
            'chat_id' => $chatId,
            'text' => $text,
            'parse_mode' => 'HTML',
            'disable_web_page_preview' => true,
        ]);

        return $response->successful();
    }

    /** @return array<int, array<string, mixed>> */
    public function updates(int $offset, int $timeout = 0): array
    {
        $response = Http::timeout($timeout + 15)->get($this->url('getUpdates'), [
            'offset' => $offset, 'timeout' => $timeout, 'allowed_updates' => json_encode(['message']),
        ]);

        return $response->successful() ? ($response->json('result') ?? []) : [];
    }

    private function url(string $method): string
    {
        return rtrim(config('panel.telegram.api'), '/').'/bot'.config('panel.telegram.token').'/'.$method;
    }
}
