<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;

class Subscriber extends Model
{
    protected $fillable = [
        'name', 'state_key', 'note', 'emails', 'keywords', 'entities', 'regions', 'include_uniq',
        'job_keywords', 'job_regions', 'job_min_salary', 'full_report', 'paused', 'last_sent_at',
    ];

    protected static function booted(): void
    {
        // la clave del estado del bot nace con el nombre y ya no cambia al renombrar
        static::creating(fn (self $s) => $s->state_key ??= $s->name);
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
        ];
    }

    public function scopeActive(Builder $query): Builder
    {
        return $query->where('paused', false);
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
}
