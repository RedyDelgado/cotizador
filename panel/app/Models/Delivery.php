<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class Delivery extends Model
{
    public const KINDS = ['diario' => 'Diario', 'pendiente' => 'Tras el pago', 'manual' => 'Manual'];

    protected $fillable = ['subscriber_id', 'subscriber_name', 'run_date', 'kind', 'email_status', 'telegram_status', 'detail'];

    protected function casts(): array
    {
        return ['run_date' => 'date'];
    }

    public function subscriber(): BelongsTo
    {
        return $this->belongsTo(Subscriber::class);
    }

    public function succeeded(): bool
    {
        return $this->email_status === 'enviado';
    }
}
