<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Requests\StoreSubscriberRequest;
use App\Http\Requests\UpdateSubscriberRequest;
use App\Http\Resources\SubscriberResource;
use App\Models\Subscriber;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\AnonymousResourceCollection;

/** API de administración (token con la habilidad "subscribers"). */
class SubscriberController extends Controller
{
    public function index(Request $request): AnonymousResourceCollection
    {
        $query = Subscriber::query()->search($request->query('q'))->orderBy('name');
        if ($request->has('paused')) {
            $query->where('paused', $request->boolean('paused'));
        }

        return SubscriberResource::collection($query->paginate(min((int) $request->query('per_page', 25), 100)));
    }

    public function store(StoreSubscriberRequest $request): JsonResponse
    {
        $subscriber = Subscriber::create($request->validated());

        return (new SubscriberResource($subscriber))->response()->setStatusCode(201);
    }

    public function show(Subscriber $subscriber): SubscriberResource
    {
        return new SubscriberResource($subscriber);
    }

    public function update(UpdateSubscriberRequest $request, Subscriber $subscriber): SubscriberResource
    {
        $subscriber->update($request->validated());

        return new SubscriberResource($subscriber);
    }

    public function destroy(Subscriber $subscriber): JsonResponse
    {
        $subscriber->delete();

        return response()->json(null, 204);
    }

    /** Pausa o reanuda los envíos: PATCH /api/subscribers/{id}/pause con {"paused": true|false}. */
    public function pause(Request $request, Subscriber $subscriber): SubscriberResource
    {
        $data = $request->validate(['paused' => ['required', 'boolean']]);
        $subscriber->update(['paused' => $data['paused']]);

        return new SubscriberResource($subscriber);
    }
}
