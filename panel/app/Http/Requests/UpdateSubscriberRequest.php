<?php

namespace App\Http\Requests;

class UpdateSubscriberRequest extends SubscriberRequest
{
    protected function ignoredId(): ?int
    {
        return $this->route('subscriber')?->id;
    }
}
