<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /** Bitácora de envíos: una fila por suscriptor y ejecución del bot (la escribe el bot por la API). */
    public function up(): void
    {
        Schema::create('deliveries', function (Blueprint $table) {
            $table->id();
            $table->foreignId('subscriber_id')->nullable()->constrained()->nullOnDelete();
            $table->string('subscriber_name', 60);        // queda aunque luego se renombre o elimine
            $table->date('run_date');                     // día (hora de Lima) en que corrió el bot
            $table->string('kind', 10);                   // diario, pendiente, manual
            $table->string('email_status', 12);           // enviado, error
            $table->string('telegram_status', 12);        // enviado, error, sin_vincular, omitido
            $table->string('detail', 500)->nullable();    // motivo del error
            $table->timestamps();
            $table->index(['run_date', 'subscriber_id']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('deliveries');
    }
};
