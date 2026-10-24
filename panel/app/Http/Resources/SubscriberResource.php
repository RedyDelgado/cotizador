<?php

namespace App\Http\Resources;

use App\Models\Subscriber;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin Subscriber */
class SubscriberResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'name' => $this->name,
            'note' => $this->note,
            'emails' => $this->emails,
            'keywords' => $this->keywords ?? [],
            'entities' => $this->entities ?? [],
            'regions' => $this->regions ?? [],
            'include_uniq' => $this->include_uniq,
            'jobs' => [
                'keywords' => $this->job_keywords ?? [],
                'regions' => $this->job_regions ?? [],
                'min_salary' => $this->job_min_salary,
            ],
            'full_report' => $this->full_report,
            'paused' => $this->paused,
            'last_sent_at' => $this->last_sent_at?->toIso8601String(),
            'created_at' => $this->created_at?->toIso8601String(),
            'updated_at' => $this->updated_at?->toIso8601String(),
        ];
    }
}
