<?php

namespace Tests\Feature;

use App\Models\Subscriber;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Http;
use Laravel\Sanctum\Sanctum;
use Tests\TestCase;

class BillingTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        $this->travelTo(now()->setDate(2026, 10, 25)->setTime(10, 0));
    }

    private function subscriber(array $extra = []): Subscriber
    {
        return Subscriber::create(array_merge(['name' => 'Ana', 'emails' => ['a@example.com'], 'keywords' => ['cemento']], $extra));
    }

    public function test_first_payment_counts_from_today_and_renewal_adds_to_the_current_period(): void
    {
        $s = $this->subscriber();
        $this->assertSame('none', $s->billingStatus());

        $first = $s->registerPayment(['method' => 'yape']); // S/ 5 por 15 días por defecto
        $this->assertSame('5.00', $first->amount);
        $this->assertSame('2026-10-25', $first->period_start->toDateString());
        $this->assertSame('2026-11-08', $s->fresh()->paid_until->toDateString()); // el día 15 es el 8 de noviembre
        $this->assertSame(14, $s->fresh()->daysLeft());

        $second = $s->fresh()->registerPayment(['method' => 'plin']);
        $this->assertSame('2026-11-09', $second->period_start->toDateString()); // se suma al final, sin perder días
        $this->assertSame('2026-11-23', $s->fresh()->paid_until->toDateString());
    }

    public function test_an_expired_subscriber_restarts_from_today(): void
    {
        $s = $this->subscriber(['paid_until' => '2026-10-01']);
        $this->assertSame('expired', $s->billingStatus());

        $s->registerPayment(['method' => 'efectivo']);
        $this->assertSame('2026-11-08', $s->fresh()->paid_until->toDateString());
    }

    public function test_billing_status_thresholds(): void
    {
        $this->assertSame('expiring', $this->subscriber(['name' => 'A', 'paid_until' => '2026-10-28'])->billingStatus());
        $this->assertSame('ok', $this->subscriber(['name' => 'B', 'paid_until' => '2026-10-29'])->billingStatus());
        $this->assertSame('expiring', $this->subscriber(['name' => 'C', 'paid_until' => '2026-10-25'])->billingStatus());
        $this->assertSame('expired', $this->subscriber(['name' => 'D', 'paid_until' => '2026-10-24'])->billingStatus());
    }

    public function test_bot_feed_only_has_subscribers_with_service_in_force(): void
    {
        $this->subscriber(['name' => 'Vigente', 'paid_until' => '2026-10-25']); // hoy es su último día: todavía recibe
        $this->subscriber(['name' => 'Vencido', 'paid_until' => '2026-10-24']);
        $this->subscriber(['name' => 'Nunca pagó']);
        $this->subscriber(['name' => 'Pausado', 'paid_until' => '2026-11-30', 'paused' => true, 'telegram_chat_id' => '123456']);
        Sanctum::actingAs(User::factory()->create(), ['bot']);

        $this->getJson('/api/bot/profiles')->assertJsonCount(1, 'data')->assertJsonPath('data.0.nombre', 'Vigente')
            ->assertJsonPath('data.0.vence', '2026-10-25');
    }

    public function test_feed_includes_the_telegram_chat(): void
    {
        $this->subscriber(['paid_until' => '2026-11-30', 'telegram_chat_id' => '98765']);
        Sanctum::actingAs(User::factory()->create(), ['bot']);

        $this->getJson('/api/bot/profiles')->assertJsonPath('data.0.telegram', '98765');
    }

    public function test_api_registers_and_lists_payments(): void
    {
        $s = $this->subscriber();
        Sanctum::actingAs(User::factory()->create(), ['subscribers']);

        $this->postJson("/api/subscribers/{$s->id}/payments", ['method' => 'yape', 'reference' => 'OP123'])
            ->assertCreated()
            ->assertJsonPath('payment.amount', 5)
            ->assertJsonPath('payment.period_end', '2026-11-08')
            ->assertJsonPath('subscriber.billing.status', 'ok')
            ->assertJsonPath('subscriber.billing.days_left', 14);
        $this->getJson("/api/subscribers/{$s->id}/payments")->assertJsonCount(1, 'data')->assertJsonPath('data.0.reference', 'OP123');

        $this->postJson("/api/subscribers/{$s->id}/payments", ['method' => 'bitcoin'])->assertJsonValidationErrors('method');
        $this->postJson("/api/subscribers/{$s->id}/payments", ['method' => 'yape', 'paid_on' => '2026-12-01'])->assertJsonValidationErrors('paid_on');
    }

    public function test_panel_registers_a_payment_and_notifies_on_telegram(): void
    {
        config(['panel.telegram.token' => 'TOKEN']);
        Http::fake(['api.telegram.org/*' => Http::response(['ok' => true])]);
        $s = $this->subscriber(['telegram_chat_id' => '555000']);
        $this->actingAs(User::factory()->create());

        $this->get("/subscribers/{$s->id}/payments")->assertOk()->assertSee('Sin pagos');
        $this->post("/subscribers/{$s->id}/payments", ['method' => 'yape', 'amount' => '5', 'days' => '15'])
            ->assertRedirect("/subscribers/{$s->id}/payments");
        $this->get('/subscribers')->assertSee('Quedan 14 d');
        $this->get("/subscribers/{$s->id}/payments")->assertSee('hasta el 08/11/2026');
        Http::assertSent(fn ($request) => str_contains($request->url(), '/botTOKEN/sendMessage')
            && $request['chat_id'] === '555000' && str_contains($request['text'], '08/11/2026'));
    }

    public function test_telegram_link_flow(): void
    {
        config(['panel.telegram.token' => 'TOKEN']);
        $s = $this->subscriber(['paid_until' => '2026-11-30']);
        Cache::forget('telegram_offset');
        Http::fake([
            'api.telegram.org/botTOKEN/getUpdates*' => Http::response(['ok' => true, 'result' => [
                ['update_id' => 10, 'message' => ['chat' => ['id' => 777111], 'text' => "/start {$s->telegram_link_code}"]],
                ['update_id' => 11, 'message' => ['chat' => ['id' => 999], 'text' => '/start CODIGOXX']],
                ['update_id' => 12, 'message' => ['chat' => ['id' => 777111], 'text' => '/estado']],
            ]]),
            'api.telegram.org/botTOKEN/sendMessage' => Http::response(['ok' => true]),
        ]);

        $this->artisan('telegram:poll --once')->assertSuccessful();

        $this->assertSame('777111', $s->fresh()->telegram_chat_id);
        $this->assertSame(13, Cache::get('telegram_offset'));
        Http::assertSent(fn ($r) => str_contains($r->url(), 'sendMessage') && $r['chat_id'] === 999 && str_contains($r['text'], 'no es válido'));
        Http::assertSent(fn ($r) => str_contains($r->url(), 'sendMessage') && $r['chat_id'] === 777111 && str_contains($r['text'], 'vigente hasta el 30/11/2026'));
    }

    public function test_reminders_go_out_once_three_days_before_and_the_day_after(): void
    {
        config(['panel.telegram.token' => 'TOKEN']);
        Http::fake(['api.telegram.org/*' => Http::response(['ok' => true])]);
        $this->subscriber(['name' => 'Por vencer', 'paid_until' => '2026-10-28', 'telegram_chat_id' => '111111']);
        $this->subscriber(['name' => 'Vencido ayer', 'paid_until' => '2026-10-24', 'telegram_chat_id' => '222222']);
        $this->subscriber(['name' => 'Lejos', 'paid_until' => '2026-11-20', 'telegram_chat_id' => '333333']);
        $this->subscriber(['name' => 'Sin telegram', 'paid_until' => '2026-10-28']);

        $this->artisan('billing:reminders')->assertSuccessful();
        $this->artisan('billing:reminders')->assertSuccessful(); // la segunda vez no repite

        Http::assertSentCount(2);
        Http::assertSent(fn ($r) => $r['chat_id'] === '111111' && str_contains($r['text'], 'vence en 3 días'));
        Http::assertSent(fn ($r) => $r['chat_id'] === '222222' && str_contains($r['text'], 'venció ayer'));
    }

    public function test_dashboard_paginates_filters_and_shows_the_numbers(): void
    {
        foreach (range(1, 12) as $n) {
            $this->subscriber(['name' => sprintf('Cliente %02d', $n), 'paid_until' => '2026-11-30', 'regions' => ['CUSCO'], 'keywords' => ['cemento']]);
        }
        $this->subscriber(['name' => 'Moroso', 'paid_until' => '2026-10-01']);
        $this->subscriber(['name' => 'Nuevo sin pago']);
        $this->subscriber(['name' => 'Por vencer', 'paid_until' => '2026-10-27']);
        $this->subscriber(['name' => 'En pausa', 'paid_until' => '2026-11-30', 'paused' => true]);
        $this->subscriber(['name' => 'Pagó', 'paid_until' => null])->registerPayment(['method' => 'yape']);
        $this->actingAs(User::factory()->create());

        $page1 = $this->get('/subscribers')->assertOk()->assertSee('Mostrando')->assertSee('1–10')->assertSee('de')->assertSee('Cobrado este mes');
        $page1->assertViewHas('stats', fn ($stats) => $stats['kpis']['total'] === 17 && $stats['kpis']['paying'] === 14
            && $stats['kpis']['expiring'] === 1 && $stats['kpis']['overdue'] === 2 && $stats['kpis']['paused'] === 1
            && $stats['kpis']['income'] === 5.0 && $stats['regions'][0]['label'] === 'Cusco' && $stats['regions'][0]['value'] === 12
            && $stats['keywords'][0]['label'] === 'cemento' && count($stats['income']) === 6 && $stats['income'][5]['value'] === 5.0);
        $page1->assertSeeInOrder(['Pagó', 'En pausa', 'Por vencer']);   // el último creado va primero
        $this->get('/subscribers?page=2')->assertSee('11–17')->assertSee('Cliente 01')->assertDontSee('Pagó');
        $this->get('/subscribers?estado=vencidos')->assertSee('Moroso')->assertDontSee('Cliente 01');
        $this->get('/subscribers?estado=sin-pago')->assertSee('Nuevo sin pago')->assertDontSee('Moroso');
        $this->get('/subscribers?estado=por-vencer')->assertSee('Por vencer')->assertDontSee('Cliente 01');
        $this->get('/subscribers?estado=pausados')->assertSee('En pausa')->assertDontSee('Cliente 01');
        $this->get('/subscribers?estado=vigentes&q=cliente%2003')->assertSee('Cliente 03')->assertDontSee('Cliente 04');
    }

    public function test_first_payment_and_reactivation_ask_for_an_immediate_report_but_a_renewal_does_not(): void
    {
        $new = $this->subscriber();
        $new->registerPayment(['method' => 'yape']);
        $this->assertTrue($new->fresh()->send_now);                       // primer pago: informe enseguida

        $new->update(['send_now' => false]);
        $new->fresh()->registerPayment(['method' => 'yape']);             // renovación con el servicio vigente
        $this->assertFalse($new->fresh()->send_now);

        $old = $this->subscriber(['name' => 'Vencido', 'paid_until' => '2026-10-01']);
        $old->registerPayment(['method' => 'plin']);                      // vuelve tras vencer
        $this->assertTrue($old->fresh()->send_now);
    }

    public function test_bot_can_ask_only_for_pending_ones_and_clears_the_flag_when_it_sends(): void
    {
        $this->subscriber(['name' => 'Pendiente', 'paid_until' => '2026-11-30', 'send_now' => true]);
        $this->subscriber(['name' => 'Normal', 'paid_until' => '2026-11-30']);
        $this->subscriber(['name' => 'Vencido', 'paid_until' => '2026-10-01', 'send_now' => true]); // sin servicio: no sale
        Sanctum::actingAs(User::factory()->create(), ['bot']);

        $this->getJson('/api/bot/profiles')->assertJsonCount(2, 'data');
        $this->getJson('/api/bot/profiles?pending=1')->assertJsonCount(1, 'data')->assertJsonPath('data.0.nombre', 'Pendiente');

        $this->postJson('/api/bot/sent', ['nombre' => 'Pendiente'])->assertOk();
        $this->getJson('/api/bot/profiles?pending=1')->assertJsonCount(0, 'data');
    }

    public function test_panel_send_now_only_works_with_the_service_in_force(): void
    {
        $active = $this->subscriber(['name' => 'Activo', 'paid_until' => '2026-11-30']);
        $expired = $this->subscriber(['name' => 'Vencido', 'paid_until' => '2026-10-01']);
        $this->actingAs(User::factory()->create());

        $this->post("/subscribers/{$active->id}/send-now")->assertRedirect()->assertSessionHas('status');
        $this->assertTrue($active->fresh()->send_now);
        $this->post("/subscribers/{$expired->id}/send-now")->assertRedirect();
        $this->assertFalse($expired->fresh()->send_now);
    }

    public function test_duplicating_does_not_copy_billing_or_telegram(): void
    {
        $s = $this->subscriber(['paid_until' => '2026-11-30', 'telegram_chat_id' => '123456']);
        $this->actingAs(User::factory()->create());

        $this->get("/subscribers/create?from={$s->id}")->assertOk()->assertSee('Ana (copia)')->assertDontSee('123456');
    }
}
