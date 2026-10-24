<?php

namespace Tests\Feature;

use App\Models\Subscriber;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class SubscriberWebTest extends TestCase
{
    use RefreshDatabase;

    public function test_guests_are_sent_to_login(): void
    {
        $this->get('/subscribers')->assertRedirect('/login');
        $this->post('/subscribers', [])->assertRedirect('/login');
    }

    public function test_admin_can_log_in_and_out(): void
    {
        User::factory()->create(['email' => 'admin@example.com', 'password' => 'secreto-largo']);

        $this->post('/login', ['email' => 'admin@example.com', 'password' => 'mala'])->assertSessionHasErrors('email');
        $this->post('/login', ['email' => 'admin@example.com', 'password' => 'secreto-largo'])->assertRedirect('/subscribers');
        $this->assertAuthenticated();
        $this->post('/logout')->assertRedirect('/login');
        $this->assertGuest();
    }

    public function test_admin_manages_subscribers_from_the_panel(): void
    {
        $this->actingAs(User::factory()->create());

        $this->get('/subscribers')->assertOk()->assertSee('Aún no hay suscriptores');
        $this->get('/subscribers/create')->assertOk()->assertSee('Compras públicas');

        // el formulario manda listas como campos repetidos (name[]) y casillas
        $this->post('/subscribers', [
            'name' => 'Grupo Indescar', 'emails' => ['g@example.com'], 'keywords' => ['cemento', 'fierro'],
            'regions' => ['CUSCO', 'APURIMAC/ABANCAY'], 'full_report' => '1', 'job_min_salary' => '',
        ])->assertRedirect('/subscribers')->assertSessionHas('status');

        $s = Subscriber::firstOrFail();
        $this->assertSame(['cemento', 'fierro'], $s->keywords);
        $this->assertTrue($s->full_report);
        $this->assertFalse($s->include_uniq);
        $this->assertNull($s->job_min_salary);

        $this->get('/subscribers')->assertSee('Grupo Indescar')->assertSee('2 regiones');
        $this->get('/subscribers?q=fierro')->assertSee('Grupo Indescar');
        $this->get('/subscribers?q=inexistente')->assertDontSee('Grupo Indescar');
        $this->get("/subscribers/{$s->id}/edit")->assertOk()->assertSee('Grupo Indescar');
        $this->get("/subscribers/create?from={$s->id}")->assertOk()->assertSee('Grupo Indescar (copia)');

        $this->put("/subscribers/{$s->id}", ['name' => 'Grupo Indescar', 'emails' => ['g@example.com'], 'keywords' => ['fierro'], 'paused' => '1'])
            ->assertRedirect('/subscribers');
        $this->assertTrue($s->fresh()->paused);

        $this->patch("/subscribers/{$s->id}/toggle")->assertRedirect();
        $this->assertFalse($s->fresh()->paused);

        $this->delete("/subscribers/{$s->id}")->assertRedirect('/subscribers');
        $this->assertDatabaseCount('subscribers', 0);
    }

    public function test_form_errors_keep_what_was_typed(): void
    {
        $this->actingAs(User::factory()->create());

        $this->from('/subscribers/create')
            ->post('/subscribers', ['name' => 'Ana', 'emails' => ['malo'], 'keywords' => ['cemento']])
            ->assertRedirect('/subscribers/create')
            ->assertSessionHasErrors('emails.0');
    }
}
