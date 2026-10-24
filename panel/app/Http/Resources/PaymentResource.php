<?php

namespace App\Http\Resources;

use App\Models\Payment;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin Payment */
class PaymentResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'subscriber_id' => $this->subscriber_id,
            'amount' => (float) $this->amount,
            'days' => $this->days,
            'method' => $this->method,
            'reference' => $this->reference,
            'paid_on' => $this->paid_on->toDateString(),
            'period_start' => $this->period_start->toDateString(),
            'period_end' => $this->period_end->toDateString(),
            'note' => $this->note,
        ];
    }
}
