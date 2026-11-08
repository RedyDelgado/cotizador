<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

class Subscriber extends Model
{
    protected $fillable = [
        'name', 'state_key', 'note', 'emails', 'keywords', 'entities', 'regions', 'include_uniq',
        'job_keywords', 'job_regions', 'job_min_salary', 'full_report', 'paused', 'last_sent_at',
        'paid_until', 'send_now', 'telegram_chat_id', 'telegram_link_code', 'last_reminder',
    ];

    protected static function booted(): void
    {
        static::creating(function (self $subscriber) {
            // la clave del estado del bot nace con el nombre y ya no cambia al renombrar
            $subscriber->state_key ??= $subscriber->name;
            $subscriber->telegram_link_code ??= Str::upper(Str::random(8));
        });
    }

    protected function casts(): array
    {
        return [
            'emails' => 'array',
            'keywords' => 'array',
            'entities' => 'array',
            'regions' => 'array',
            'job_keywords' => 'array',
            'job_regions' => 'array',
            'include_uniq' => 'boolean',
            'full_report' => 'boolean',
            'paused' => 'boolean',
            'job_min_salary' => 'integer',
            'last_sent_at' => 'datetime',
            'paid_until' => 'date',
            'send_now' => 'boolean',
        ];
    }

    public function payments(): HasMany
    {
        return $this->hasMany(Payment::class)->latest('paid_on')->latest('id');
    }

    public function scopeActive(Builder $query): Builder
    {
        return $query->where('paused', false);
    }

    /** Lo que se le envía hoy: no está en pausa y su pago sigue vigente (el último día cuenta). */
    public function scopeDeliverable(Builder $query): Builder
    {
        return $query->where('paused', false)->whereDate('paid_until', '>=', today());
    }

    /** Filtro de la tabla por estado de cobro: vigentes, por-vencer, vencidos, sin-pago o pausados. */
    public function scopeBilling(Builder $query, ?string $status): Builder
    {
        return match ($status) {
            'vigentes' => $query->deliverable(),
            'por-vencer' => $query->active()->whereDate('paid_until', '>=', today())->whereDate('paid_until', '<=', today()->addDays(config('panel.expiring_days'))),
            'vencidos' => $query->whereDate('paid_until', '<', today()),
            'sin-pago' => $query->whereNull('paid_until'),
            'pausados' => $query->where('paused', true),
            default => $query,
        };
    }

    /** Busca por nombre, correo o cualquier interés (los arrays JSON se guardan como texto). */
    public function scopeSearch(Builder $query, ?string $term): Builder
    {
        $term = trim((string) $term);

        return $term === '' ? $query : $query->where(function (Builder $q) use ($term) {
            $like = '%'.str_replace(['%', '_'], ['\%', '\_'], $term).'%';
            foreach (['name', 'note', 'emails', 'keywords', 'entities', 'regions', 'job_keywords', 'job_regions'] as $column) {
                $q->orWhere($column, 'like', $like);
            }
        });
    }

    public function hasJobs(): bool
    {
        return ! empty($this->job_keywords) || ! empty($this->job_regions) || $this->job_min_salary;
    }

    /** Días que le quedan (0 = hoy es su último día; negativo = ya venció; null = nunca pagó). */
    public function daysLeft(): ?int
    {
        return $this->paid_until ? (int) today()->diffInDays($this->paid_until, false) : null;
    }

    /** none (nunca pagó), expired, expiring (le quedan pocos días) u ok. */
    public function billingStatus(): string
    {
        $left = $this->daysLeft();

        return match (true) {
            $left === null => 'none',
            $left < 0 => 'expired',
            $left <= config('panel.expiring_days') => 'expiring',
            default => 'ok',
        };
    }

    /**
     * Registra un pago y extiende el servicio: si aún está vigente, los días se suman al final del período actual;
     * si venció (o nunca pagó), cuentan desde hoy.
     *
     * @param  array{amount?: float|int|string, days?: int, method: string, reference?: ?string, paid_on?: mixed, note?: ?string}  $data
     */
    public function registerPayment(array $data): Payment
    {
        return DB::transaction(function () use ($data): Payment {
            $wasInactive = ! $this->paid_until || $this->paid_until->lt(today()); // primer pago o reactivación
            $days = (int) ($data['days'] ?? config('panel.days'));
            $start = $this->paid_until && $this->paid_until->gte(today()) ? $this->paid_until->copy()->addDay() : today();
            $end = $start->copy()->addDays($days - 1);

            $payment = $this->payments()->create([
                'amount' => $data['amount'] ?? config('panel.price'),
                'days' => $days,
                'method' => $data['method'],
                'reference' => $data['reference'] ?? null,
                'paid_on' => $data['paid_on'] ?? today(),
                'period_start' => $start,
                'period_end' => $end,
                'note' => $data['note'] ?? null,
            ]);
            // al empezar (o volver) el servicio recibe su informe enseguida, sin esperar a mañana
            $this->update(['paid_until' => $end, 'last_reminder' => null, 'send_now' => $this->send_now || $wasInactive]);

            return $payment;
        });
    }
}
