<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /** Clave estable con la que el bot guarda "lo ya informado": no cambia aunque renombres al suscriptor. */
    public function up(): void
    {
        Schema::table('subscribers', function (Blueprint $table) {
            $table->string('state_key', 60)->nullable()->after('name');
        });
        DB::table('subscribers')->update(['state_key' => DB::raw('name')]);
    }

    public function down(): void
    {
        Schema::table('subscribers', function (Blueprint $table) {
            $table->dropColumn('state_key');
        });
    }
};
