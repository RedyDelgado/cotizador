<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Resources\BotProfileResource;
use App\Models\Subscriber;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\AnonymousResourceCollection;

/** Lo que usa el bot de Python (token con la habilidad "bot"). */
class BotController extends Controller
{
    /** Suscriptores activos, con las mismas claves de perfiles.ini. Los pausados no salen: el bot no les envía nada. */
    public function profiles(): AnonymousResourceCollection
    {
        return BotProfileResource::collection(Subscriber::active()->orderBy('name')->get());
    }

    /** El bot avisa que ya envió el informe de ese suscriptor (se ve en el panel como "último envío"). */
    public function sent(Request $request): JsonResponse
    {
        $data = $request->validate(['nombre' => ['required', 'string', 'max:60']]);
        $updated = Subscriber::where('name', $data['nombre'])->update(['last_sent_at' => now()]);

        return response()->json(['updated' => $updated], $updated ? 200 : 404);
    }
}
