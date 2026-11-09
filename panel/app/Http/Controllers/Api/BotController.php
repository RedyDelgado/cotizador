<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Resources\BotProfileResource;
use App\Models\Delivery;
use App\Models\Subscriber;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\AnonymousResourceCollection;
use Illuminate\Validation\Rule;

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

    /** El bot informa cómo le fue con un suscriptor (módulo «Envíos»); si el correo salió, también su «último envío». */
    public function delivery(Request $request): JsonResponse
    {
        $data = $request->validate([
            'nombre' => ['required', 'string', 'max:60'],
            'clave' => ['nullable', 'string', 'max:60'],
            'tipo' => ['required', Rule::in(array_keys(Delivery::KINDS))],
            'correo' => ['required', Rule::in(['enviado', 'error'])],
            'telegram' => ['required', Rule::in(['enviado', 'error', 'sin_vincular', 'omitido'])],
            'detalle' => ['nullable', 'string', 'max:500'],
        ]);
        $subscriber = Subscriber::where('state_key', $data['clave'] ?? $data['nombre'])->first()
            ?? Subscriber::where('name', $data['nombre'])->first();

        $delivery = Delivery::create([
            'subscriber_id' => $subscriber?->id,
            'subscriber_name' => $subscriber->name ?? $data['nombre'],
            'run_date' => today(),
            'kind' => $data['tipo'],
            'email_status' => $data['correo'],
            'telegram_status' => $data['telegram'],
            'detail' => $data['detalle'] ?? null,
        ]);
        if ($subscriber && $delivery->succeeded()) {
            $subscriber->update(['last_sent_at' => now(), 'send_now' => false]);
        }

        return response()->json(['id' => $delivery->id], 201);
    }
}
