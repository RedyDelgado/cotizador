<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('subscribers', function (Blueprint $table) {
            $table->date('paid_until')->nullable()->after('paused');          // último día con el servicio vigente
            $table->string('telegram_chat_id', 30)->nullable()->after('paid_until');
            $table->string('telegram_link_code', 16)->nullable()->unique()->after('telegram_chat_id');
            $table->string('last_reminder', 20)->nullable()->after('telegram_link_code'); // "2026-10-27:3": evita avisar dos veces
        });

        // Los suscriptores que ya existían reciben 15 días de gracia, para que el corte no los tome por sorpresa.
        DB::table('subscribers')->update(['paid_until' => now()->addDays(15)->toDateString()]);

        Schema::create('payments', function (Blueprint $table) {
            $table->id();
            $table->foreignId('subscriber_id')->constrained()->cascadeOnDelete();
            $table->decimal('amount', 8, 2);
            $table->unsignedSmallInteger('days');
            $table->string('method', 20);                 // yape, plin, transferencia, efectivo, otro
            $table->string('reference', 60)->nullable();  // N.º de operación
            $table->date('paid_on');
            $table->date('period_start');
            $table->date('period_end');
            $table->string('note', 120)->nullable();
            $table->timestamps();
            $table->index('paid_on');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('payments');
        Schema::table('subscribers', function (Blueprint $table) {
            $table->dropColumn(['paid_until', 'telegram_chat_id', 'telegram_link_code', 'last_reminder']);
        });
    }
};
