<?php

namespace Tests\Feature;

use App\Models\Subscriber;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Laravel\Sanctum\Sanctum;
use Tests\TestCase;

class BotApiTest extends TestCase
{
    use RefreshDatabase;

    public function test_bot_gets_active_profiles_in_perfiles_ini_format(): void
    {
        Subscriber::create([
            'name' => 'Ana', 'note' => 'Cliente', 'emails' => ['a@example.com', 'b@example.com'],
            'keywords' => ['cemento', '"sistema académico"'], 'entities' => ['UGEL LA CONVENCION'],
            'regions' => ['CUSCO', 'APURIMAC/ABANCAY'], 'include_uniq' => true,
            'job_keywords' => ['ingeniero'], 'job_regions' => ['CUSCO'], 'job_min_salary' => 3000, 'full_report' => false,
            'paid_until' => today()->addDays(5), 'telegram_chat_id' => '4242',
        ]);
        Subscriber::create(['name' => 'Pausado', 'emails' => ['p@example.com'], 'keywords' => ['x'], 'paused' => true]);
        Sanctum::actingAs(User::factory()->create(), ['bot']);

        $this->getJson('/api/bot/profiles')
            ->assertOk()
            ->assertJsonCount(1, 'data')
            ->assertJsonPath('data.0', [
                'nombre' => 'Ana',
                'clave' => 'Ana',
                'nota' => 'Cliente',
                'correos' => 'a@example.com, b@example.com',
                'palabras_clave' => 'cemento,"sistema académico"',
                'entidades' => 'UNIQ,UGEL LA CONVENCION',
                'regiones' => 'CUSCO,APURIMAC/ABANCAY',
                'empleo_palabras' => 'ingeniero',
                'empleo_regiones' => 'CUSCO',
                'empleo_sueldo_min' => '3000',
                'completo' => 'no',
                'telegram' => '4242',
                'vence' => today()->addDays(5)->toDateString(),
            ]);
    }

    public function test_renaming_keeps_the_bot_state_key(): void
    {
        $s = Subscriber::create(['name' => 'Ana', 'emails' => ['a@example.com'], 'keywords' => ['x'], 'paid_until' => today()->addDay()]);
        $s->update(['name' => 'Ana María']);
        Sanctum::actingAs(User::factory()->create(), ['bot']);

        $this->getJson('/api/bot/profiles')->assertJsonPath('data.0.nombre', 'Ana María')->assertJsonPath('data.0.clave', 'Ana');
    }

    public function test_exports_active_subscribers_as_perfiles_ini(): void
    {
        Subscriber::create(['name' => 'Ana', 'emails' => ['a@example.com'], 'keywords' => ['cemento'], 'regions' => ['CUSCO'], 'paid_until' => today()->addDay()]);
        Subscriber::create(['name' => 'Pausado', 'emails' => ['p@example.com'], 'keywords' => ['x'], 'paused' => true]);
        $path = tempnam(sys_get_temp_dir(), 'ini');

        $this->artisan('panel:export-perfiles', ['path' => $path])->assertSuccessful();

        $ini = parse_ini_file($path, true, INI_SCANNER_RAW);
        $this->assertSame(['Ana'], array_keys($ini));
        $this->assertSame('cemento', $ini['Ana']['palabras_clave']);
        $this->assertSame('Ana', $ini['Ana']['clave']);
        unlink($path);
    }

    public function test_bot_token_cannot_manage_subscribers_and_admin_token_cannot_read_bot_feed(): void
    {
        Sanctum::actingAs(User::factory()->create(), ['bot']);
        $this->getJson('/api/subscribers')->assertForbidden();

        Sanctum::actingAs(User::factory()->create(), ['subscribers']);
        $this->getJson('/api/bot/profiles')->assertForbidden();
    }

    public function test_bot_reports_what_it_sent(): void
    {
        Subscriber::create(['name' => 'Ana', 'emails' => ['a@example.com'], 'keywords' => ['x']]);
        Sanctum::actingAs(User::factory()->create(), ['bot']);

        $this->postJson('/api/bot/sent', ['nombre' => 'Ana'])->assertOk();
        $this->assertNotNull(Subscriber::first()->last_sent_at);
        $this->postJson('/api/bot/sent', ['nombre' => 'Nadie'])->assertNotFound();
    }

    public function test_plain_token_from_the_seeder_authenticates(): void
    {
        config(['app.env' => 'testing']);
        putenv('ADMIN_EMAIL=admin@example.com');
        putenv('PANEL_BOT_TOKEN=token-de-prueba');
        $this->seed();
        putenv('ADMIN_EMAIL');
        putenv('PANEL_BOT_TOKEN');

        $this->withToken('token-de-prueba')->getJson('/api/bot/profiles')->assertOk();
        $this->app['auth']->forgetGuards();
        $this->withToken('otro')->getJson('/api/bot/profiles')->assertUnauthorized();
    }
}
