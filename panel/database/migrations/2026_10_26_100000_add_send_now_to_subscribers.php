<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('subscribers', function (Blueprint $table) {
            // El panel lo activa (primer pago, reactivación o «Enviar ahora»); el bot lo ve cada pocos minutos,
            // envía el informe en ese momento y lo apaga.
            $table->boolean('send_now')->default(false)->after('paid_until');
        });
    }

    public function down(): void
    {
        Schema::table('subscribers', function (Blueprint $table) {
            $table->dropColumn('send_now');
        });
    }
};
