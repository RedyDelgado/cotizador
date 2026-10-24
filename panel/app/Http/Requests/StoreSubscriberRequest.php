<?php

namespace App\Http\Requests;

class StoreSubscriberRequest extends SubscriberRequest
{
    protected function ignoredId(): ?int
    {
        return null;
    }
}
