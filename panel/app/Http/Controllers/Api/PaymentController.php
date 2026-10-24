<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Requests\StorePaymentRequest;
use App\Http\Resources\PaymentResource;
use App\Http\Resources\SubscriberResource;
use App\Models\Subscriber;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Resources\Json\AnonymousResourceCollection;

class PaymentController extends Controller
{
    public function index(Subscriber $subscriber): AnonymousResourceCollection
    {
        return PaymentResource::collection($subscriber->payments()->get());
    }

    /** Registra un pago (por defecto S/ 5 por 15 días) y devuelve el suscriptor con su nuevo vencimiento. */
    public function store(StorePaymentRequest $request, Subscriber $subscriber): JsonResponse
    {
        $payment = $subscriber->registerPayment($request->paymentData());

        return response()->json([
            'payment' => new PaymentResource($payment),
            'subscriber' => new SubscriberResource($subscriber->refresh()),
        ], 201);
    }
}
