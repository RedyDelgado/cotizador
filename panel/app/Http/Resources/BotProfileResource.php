<?php

namespace App\Http\Resources;

use App\Models\Subscriber;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/**
 * El suscriptor tal como lo lee el bot de Python: las mismas claves y el mismo texto que un bloque de perfiles.ini
 * (listas separadas por coma), así el bot las valida con las reglas de siempre.
 *
 * @mixin Subscriber
 */
class BotProfileResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        $join = fn (?array $list) => implode(',', $list ?? []);
        $entities = array_merge($this->include_uniq ? ['UNIQ'] : [], $this->entities ?? []);

        return array_filter([
            'nombre' => $this->name,
            'clave' => $this->state_key ?? $this->name,
            'nota' => $this->note,
            'correos' => implode(', ', $this->emails),
            'palabras_clave' => $join($this->keywords),
            'entidades' => $join($entities),
            'regiones' => $join($this->regions),
            'empleo_palabras' => $join($this->job_keywords),
            'empleo_regiones' => $join($this->job_regions),
            'empleo_sueldo_min' => $this->job_min_salary ? (string) $this->job_min_salary : '',
            'completo' => $this->full_report ? 'si' : 'no',
        ], fn ($v) => $v !== null && $v !== '');
    }
}
