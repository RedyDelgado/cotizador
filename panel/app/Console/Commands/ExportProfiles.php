<?php

namespace App\Console\Commands;

use App\Http\Resources\BotProfileResource;
use App\Models\Subscriber;
use Illuminate\Console\Command;
use Illuminate\Http\Request;

class ExportProfiles extends Command
{
    protected $signature = 'panel:export-perfiles {path : Dónde escribir el perfiles.ini (p. ej. /opt/cotizaciones-uniq/perfiles.ini)}';

    protected $description = 'Escribe los suscriptores activos como perfiles.ini para el bot, sin necesidad de HTTP';

    public function handle(): int
    {
        $blocks = Subscriber::active()->orderBy('name')->get()->map(function (Subscriber $subscriber): string {
            $data = (new BotProfileResource($subscriber))->toArray(new Request);
            $name = $data['nombre'];
            unset($data['nombre']);

            return "[{$name}]\n".collect($data)->map(fn ($value, $key) => "{$key} = {$value}\n")->implode('');
        });

        if ($blocks->isEmpty()) {
            $this->error('No hay suscriptores activos: no se escribe nada (el bot no se ejecuta con el archivo vacío).');

            return self::FAILURE;
        }

        $path = $this->argument('path');
        file_put_contents($path.'.tmp', "; Generado por el panel (php artisan panel:export-perfiles). No lo edites a mano.\n\n".$blocks->implode("\n"));
        rename($path.'.tmp', $path);
        $this->info("{$blocks->count()} suscriptores escritos en {$path}.");

        return self::SUCCESS;
    }
}
