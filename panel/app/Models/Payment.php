<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Payment extends Model
{
    protected $fillable = ['subscriber_id', 'amount', 'days', 'method', 'reference', 'paid_on', 'period_start', 'period_end', 'note'];

    protected function casts(): array
    {
        return [
            'amount' => 'decimal:2',
            'days' => 'integer',
            'paid_on' => 'date',
            'period_start' => 'date',
            'period_end' => 'date',
        ];
    }

    public function subscriber(): BelongsTo
    {
        return $this->belongsTo(Subscriber::class);
    }
}
