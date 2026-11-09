<?php

namespace Tests\Feature;

use App\Models\Delivery;
use App\Models\Subscriber;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Laravel\Sanctum\Sanctum;
use Tests\TestCase;

class DeliveryTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        $this->travelTo(now()->setDate(2026, 11, 9)->setTime(10, 0));
    }

    private function subscriber(array $extra = []): Subscriber
    {
        return Subscriber::create(array_merge(['name' => 'Ana', 'emails' => ['a@example.com'], 'keywords' => ['cemento'], 'paid_until' => '2026-11-30'], $extra));
    }

    public function test_bot_records_each_delivery_and_updates_last_sent_only_when_the_email_went_out(): void
    {
        $ana = $this->subscriber();
        $ana->update(['name' => 'Ana María']);            // la clave de estado sigue siendo «Ana»
        Sanctum::actingAs(User::factory()->create(), ['bot']);

        $this->postJson('/api/bot/delivery', ['nombre' => 'Ana María', 'clave' => 'Ana', 'tipo' => 'diario', 'correo' => 'enviado', 'telegram' => 'sin_vincular'])
            ->assertCreated();
        $this->assertNotNull($ana->fresh()->last_sent_at);
        $this->assertDatabaseHas('deliveries', ['subscriber_id' => $ana->id, 'kind' => 'diario', 'email_status' => 'enviado', 'run_date' => '2026-11-09 00:00:00']);

        $luis = $this->subscriber(['name' => 'Luis']);
        $this->postJson('/api/bot/delivery', ['nombre' => 'Luis', 'tipo' => 'pendiente', 'correo' => 'error', 'telegram' => 'omitido', 'detalle' => 'SMTPAuthenticationError'])
            ->assertCreated();
        $this->assertNull($luis->fresh()->last_sent_at);

        $this->postJson('/api/bot/delivery', ['nombre' => 'X', 'tipo' => 'otro', 'correo' => 'quizás', 'telegram' => 'enviado'])
            ->assertJsonValidationErrors(['tipo', 'correo']);
    }

    public function test_only_the_bot_token_can_record_deliveries(): void
    {
        $this->postJson('/api/bot/delivery', [])->assertUnauthorized();
        Sanctum::actingAs(User::factory()->create(), ['subscribers']);
        $this->postJson('/api/bot/delivery', [])->assertForbidden();
    }

    public function test_page_shows_sent_failed_and_missing_by_date(): void
    {
        $ana = $this->subscriber();
        $luis = $this->subscriber(['name' => 'Luis', 'emails' => ['l@example.com']]);
        $this->subscriber(['name' => 'Vencido', 'paid_until' => '2026-11-01']);      // no debía recibir
        $this->subscriber(['name' => 'Pausado', 'paused' => true]);                    // no debía recibir
        Subscriber::query()->update(['created_at' => '2026-11-01 08:00:00']);          // ya existían días antes
        Delivery::create(['subscriber_id' => $ana->id, 'subscriber_name' => 'Ana', 'run_date' => '2026-11-09', 'kind' => 'diario',
            'email_status' => 'enviado', 'telegram_status' => 'enviado']);
        Delivery::create(['subscriber_id' => $luis->id, 'subscriber_name' => 'Luis', 'run_date' => '2026-11-09', 'kind' => 'diario',
            'email_status' => 'error', 'telegram_status' => 'omitido', 'detail' => 'SMTPAuthenticationError']);
        $this->actingAs(User::factory()->create());

        $this->get('/envios')->assertOk()
            ->assertViewHas('stats', ['sent' => 1, 'failed' => 1, 'missing' => 1, 'telegram' => 1])
            ->assertSee('SMTPAuthenticationError')
            ->assertSeeInOrder(['Sin envío este día', 'Luis'])
            ->assertDontSee('Vencido')
            ->assertDontSee('no se registró este día');

        // un día sin ejecución: se avisa y aparecen todos los que debían recibir
        $this->get('/envios?fecha=2026-11-08')->assertOk()
            ->assertViewHas('stats', fn ($s) => $s['sent'] === 0 && $s['missing'] === 2)
            ->assertSee('no se registró este día');

        $this->get('/envios?fecha=2099-01-01')->assertOk()->assertViewHas('date', fn ($d) => $d->isToday());   // futuro: hoy
        $this->get('/envios?fecha=basura')->assertOk()->assertViewHas('date', fn ($d) => $d->isToday());
    }

    public function test_guests_cannot_see_deliveries(): void
    {
        $this->get('/envios')->assertRedirect('/login');
    }
}
