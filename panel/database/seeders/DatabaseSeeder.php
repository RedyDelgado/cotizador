<?php

namespace Database\Seeders;

use App\Models\Subscriber;
use App\Models\User;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;

/**
 * Crea (sin duplicar) tu usuario administrador y, si defines PANEL_BOT_TOKEN, el token que usa el bot.
 * Datos de demostración solo con SEED_DEMO=1 (pruebas locales).
 */
class DatabaseSeeder extends Seeder
{
    public function run(): void
    {
        if ($email = env('ADMIN_EMAIL')) {
            User::updateOrCreate(['email' => $email], [
                'name' => env('ADMIN_NAME', 'Administrador'),
                'password' => Hash::make(env('ADMIN_PASSWORD', 'cambiar-esto')),
            ]);
        }

        if (($plain = env('PANEL_BOT_TOKEN')) && ($admin = User::first())) {
            $this->tokenWithKnownValue($admin, 'bot', ['bot'], $plain);
        }

        if (env('SEED_DEMO')) {
            Subscriber::firstOrCreate(['name' => 'demo compras'], [
                'note' => 'Demostración: compras públicas en Cusco',
                'emails' => ['demo@example.com'],
                'keywords' => ['cemento', 'fierro', '"sistema académico"'],
                'regions' => ['CUSCO'],
                'include_uniq' => true,
            ]);
            Subscriber::firstOrCreate(['name' => 'demo empleos'], [
                'note' => 'Demostración: ofertas de empleo',
                'emails' => ['empleo@example.com'],
                'job_keywords' => ['ingeniero', 'abogado'],
                'job_regions' => ['CUSCO'],
                'job_min_salary' => 3000,
                'full_report' => false,
            ]);
        }
    }

    /** Sanctum guarda solo el hash: así el token de las pruebas locales es el valor que tú eliges. */
    private function tokenWithKnownValue(User $user, string $name, array $abilities, string $plain): void
    {
        $user->tokens()->where('name', $name)->delete();
        $user->tokens()->create([
            'name' => $name,
            'token' => hash('sha256', $plain),
            'abilities' => $abilities,
        ]);
    }
}
