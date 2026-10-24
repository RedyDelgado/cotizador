<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('subscribers', function (Blueprint $table) {
            $table->id();
            $table->string('name', 60)->unique();
            $table->string('note', 120)->nullable();
            $table->json('emails');                      // a quién llega el informe
            $table->json('keywords')->nullable();        // palabras clave de compras públicas (SEACE, UNIQ)
            $table->json('entities')->nullable();        // entidades que sigue
            $table->json('regions')->nullable();         // "CUSCO" o "APURIMAC/ABANCAY"
            $table->boolean('include_uniq')->default(false);
            $table->json('job_keywords')->nullable();    // ofertas de empleo
            $table->json('job_regions')->nullable();
            $table->unsignedInteger('job_min_salary')->nullable();
            $table->boolean('full_report')->default(true);
            $table->boolean('paused')->default(false);
            $table->timestamp('last_sent_at')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('subscribers');
    }
};
