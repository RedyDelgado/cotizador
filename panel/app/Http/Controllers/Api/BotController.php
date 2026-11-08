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
    /** Suscriptores con servicio vigente (no pausados y con el pago al día), con las claves de perfiles.ini. Al vencer dejan de salir. */
    public function profiles(Request $request): AnonymousResourceCollection
    {
        $query = Subscriber::deliverable()->orderBy('name');
        if ($request->boolean('pending')) { // solo a quienes hay que enviarles ya (primer pago, reactivación, «Enviar ahora»)
            $query->where('send_now', true);
        }

        return BotProfileResource::collection($query->get());
    }

    /** El bot avisa que ya envió el informe de ese suscriptor (se ve en el panel como "último envío"). */
    public function sent(Request $request): JsonResponse
    {
        $data = $request->validate(['nombre' => ['required', 'string', 'max:60']]);
        $updated = Subscriber::where('name', $data['nombre'])->update(['last_sent_at' => now(), 'send_now' => false]);

        return response()->json(['updated' => $updated], $updated ? 200 : 404);
    }
}
