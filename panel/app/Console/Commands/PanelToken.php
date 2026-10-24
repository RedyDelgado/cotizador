<?php

namespace App\Console\Commands;

use App\Models\User;
use Illuminate\Console\Command;

class PanelToken extends Command
{
    protected $signature = 'panel:token {name : Nombre del token (p. ej. bot)} {--abilities=bot : Habilidades separadas por coma: bot, subscribers} {--user= : Correo del usuario dueño (por defecto, el primero)}';

    protected $description = 'Crea un token de API y lo muestra una sola vez';

    public function handle(): int
    {
        $user = $this->option('user') ? User::where('email', $this->option('user'))->first() : User::first();
        if (! $user) {
            $this->error('No hay usuarios: crea el administrador primero (ADMIN_EMAIL en .env y php artisan db:seed).');

            return self::FAILURE;
        }
        $abilities = array_values(array_filter(explode(',', (string) $this->option('abilities'))));
        $invalid = array_diff($abilities, ['bot', 'subscribers']);
        if ($invalid) {
            $this->error('Habilidad desconocida: '.implode(', ', $invalid).' (válidas: bot, subscribers).');

            return self::FAILURE;
        }

        $token = $user->createToken($this->argument('name'), $abilities)->plainTextToken;
        $this->info('Token creado (guárdalo: no se vuelve a mostrar):');
        $this->line($token);

        return self::SUCCESS;
    }
}
