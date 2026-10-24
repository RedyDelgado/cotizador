<?php

namespace Tests\Feature;

use App\Models\Subscriber;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Laravel\Sanctum\Sanctum;
use Tests\TestCase;

class SubscriberApiTest extends TestCase
{
    use RefreshDatabase;

    private function payload(array $extra = []): array
    {
        return array_merge([
            'name' => 'Ana',
            'emails' => ['ana@example.com'],
            'keywords' => ['cemento', '"sistema académico"'],
            'regions' => ['cusco', 'apurímac/abancay'],
        ], $extra);
    }

    private function asAdmin(): void
    {
        Sanctum::actingAs(User::factory()->create(), ['subscribers']);
    }

    public function test_requires_a_token_with_the_right_ability(): void
    {
        $this->getJson('/api/subscribers')->assertUnauthorized();

        Sanctum::actingAs(User::factory()->create(), ['bot']);
        $this->getJson('/api/subscribers')->assertForbidden();
    }

    public function test_creates_a_subscriber_and_canonicalizes_regions(): void
    {
        $this->asAdmin();

        $this->postJson('/api/subscribers', $this->payload())
            ->assertCreated()
            ->assertJsonPath('data.name', 'Ana')
            ->assertJsonPath('data.regions', ['CUSCO', 'APURIMAC/ABANCAY'])
            ->assertJsonPath('data.jobs.min_salary', null);

        $this->assertDatabaseCount('subscribers', 1);
    }

    public function test_accepts_comma_or_line_separated_text_for_lists(): void
    {
        $this->asAdmin();

        $this->postJson('/api/subscribers', $this->payload([
            'emails' => "a@example.com, b@example.com\nA@example.com",
            'keywords' => "cemento\nfierro, cemento",
        ]))->assertCreated()
            ->assertJsonPath('data.emails', ['a@example.com', 'b@example.com', 'A@example.com'])
            ->assertJsonPath('data.keywords', ['cemento', 'fierro']);
    }

    public function test_validates_input(): void
    {
        $this->asAdmin();
        Subscriber::create(['name' => 'Ana', 'emails' => ['x@example.com'], 'keywords' => ['a']]);

        $this->postJson('/api/subscribers', $this->payload())->assertJsonValidationErrors('name');
        $this->postJson('/api/subscribers', $this->payload(['name' => 'B', 'emails' => ['no-es-correo']]))->assertJsonValidationErrors('emails.0');
        $this->postJson('/api/subscribers', $this->payload(['name' => 'B', 'emails' => []]))->assertJsonValidationErrors('emails');
        $this->postJson('/api/subscribers', $this->payload(['name' => 'B', 'regions' => ['NARNIA']]))->assertJsonValidationErrors('regions.0');
        $this->postJson('/api/subscribers', $this->payload(['name' => 'B', 'regions' => ['CUSCO/NO EXISTE']]))->assertJsonValidationErrors('regions.0');
        $this->postJson('/api/subscribers', $this->payload(['name' => 'B', 'job_min_salary' => 'mucho']))->assertJsonValidationErrors('job_min_salary');
        $this->postJson('/api/subscribers', $this->payload(['name' => 'Bad]']))->assertJsonValidationErrors('name');
    }

    public function test_must_follow_something(): void
    {
        $this->asAdmin();

        $this->postJson('/api/subscribers', ['name' => 'Vacío', 'emails' => ['v@example.com']])->assertJsonValidationErrors('keywords');
        $this->postJson('/api/subscribers', ['name' => 'Solo UNIQ', 'emails' => ['v@example.com'], 'include_uniq' => true])->assertCreated();
        $this->postJson('/api/subscribers', ['name' => 'Solo empleo', 'emails' => ['w@example.com'], 'job_min_salary' => 3000])->assertCreated();
    }

    public function test_updates_pauses_searches_and_deletes(): void
    {
        $this->asAdmin();
        $id = $this->postJson('/api/subscribers', $this->payload())->json('data.id');
        $this->postJson('/api/subscribers', $this->payload(['name' => 'Luis', 'emails' => ['l@example.com']]));

        // el nombre propio no cuenta como repetido al editar; el de otro sí
        $this->putJson("/api/subscribers/$id", $this->payload(['note' => 'Cliente']))->assertOk()->assertJsonPath('data.note', 'Cliente');
        $this->putJson("/api/subscribers/$id", $this->payload(['name' => 'Luis']))->assertJsonValidationErrors('name');

        $this->patchJson("/api/subscribers/$id/pause", ['paused' => true])->assertOk()->assertJsonPath('data.paused', true);
        $this->getJson('/api/subscribers?paused=1')->assertJsonCount(1, 'data');
        $this->getJson('/api/subscribers?q=cemento')->assertJsonCount(2, 'data');
        $this->getJson('/api/subscribers?q=luis')->assertJsonCount(1, 'data');

        $this->deleteJson("/api/subscribers/$id")->assertNoContent();
        $this->getJson("/api/subscribers/$id")->assertNotFound();
    }
}
