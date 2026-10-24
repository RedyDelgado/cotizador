<?php

namespace App\Http\Requests;

use App\Rules\ValidRegion;
use App\Support\Regions;
use Illuminate\Contracts\Validation\Validator;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

/** Reglas comunes de alta y edición de suscriptores (las usan el panel web y la API). */
abstract class SubscriberRequest extends FormRequest
{
    private const LISTS = ['emails', 'keywords', 'entities', 'regions', 'job_keywords', 'job_regions'];

    abstract protected function ignoredId(): ?int;

    public function authorize(): bool
    {
        return true; // el acceso lo controlan las rutas (sesión o token)
    }

    /** Acepta listas (JSON/campos repetidos) o texto separado por comas o líneas, y las deja limpias. */
    protected function prepareForValidation(): void
    {
        $clean = [];
        foreach (self::LISTS as $field) {
            if (! $this->has($field)) {
                continue;
            }
            $value = $this->input($field);
            $items = is_array($value) ? $value : preg_split('/[\r\n,]+/', (string) $value);
            $items = array_map(fn ($i) => is_string($i) ? trim(preg_replace('/\s+/', ' ', str_replace(',', ' ', $i))) : $i, $items);
            $items = array_values(array_unique(array_filter($items, fn ($i) => $i !== '' && $i !== null)));
            if (in_array($field, ['regions', 'job_regions'], true)) {
                $items = array_map(fn ($r) => is_string($r) ? (Regions::canonical($r) ?? $r) : $r, $items);
            }
            $clean[$field] = $items;
        }
        foreach (['include_uniq', 'full_report', 'paused'] as $flag) {
            $clean[$flag] = $this->boolean($flag);
        }
        if ($this->has('job_min_salary')) {
            $clean['job_min_salary'] = $this->input('job_min_salary') === '' ? null : $this->input('job_min_salary');
        }
        $this->merge($clean);
    }

    public function rules(): array
    {
        $words = ['nullable', 'array', 'max:60'];
        $word = ['string', 'max:80'];

        return [
            'name' => ['required', 'string', 'max:60', 'not_regex:/[\[\]]/', Rule::unique('subscribers', 'name')->ignore($this->ignoredId())],
            'note' => ['nullable', 'string', 'max:120'],
            'emails' => ['required', 'array', 'min:1', 'max:20'],
            'emails.*' => ['email:rfc', 'max:120'],
            'keywords' => $words, 'keywords.*' => $word,
            'entities' => $words, 'entities.*' => $word,
            'regions' => $words, 'regions.*' => [new ValidRegion],
            'include_uniq' => ['boolean'],
            'job_keywords' => $words, 'job_keywords.*' => $word,
            'job_regions' => $words, 'job_regions.*' => [new ValidRegion],
            'job_min_salary' => ['nullable', 'integer', 'min:0', 'max:1000000'],
            'full_report' => ['boolean'],
            'paused' => ['boolean'],
        ];
    }

    /** Un suscriptor tiene que seguir algo: si no, el bot no tendría qué buscarle. */
    public function after(): array
    {
        return [function (Validator $validator) {
            $follows = $this->boolean('include_uniq') || $this->filled('keywords') || $this->filled('entities') || $this->filled('regions')
                || $this->filled('job_keywords') || $this->filled('job_regions') || $this->filled('job_min_salary');
            if (! $follows) {
                $validator->errors()->add('keywords', 'Elige algo que seguir: palabras clave, entidades, regiones, empleos o la UNIQ.');
            }
        }];
    }

    public function messages(): array
    {
        return [
            'name.required' => 'Escribe un nombre.',
            'name.unique' => 'Ya existe un suscriptor con ese nombre.',
            'name.not_regex' => 'El nombre no puede llevar corchetes.',
            'emails.required' => 'Agrega al menos un correo.',
            'emails.min' => 'Agrega al menos un correo.',
            'emails.*.email' => 'El correo «:input» no es válido.',
            'job_min_salary.integer' => 'El sueldo mínimo tiene que ser un número entero.',
        ];
    }

    public function attributes(): array
    {
        return [
            'name' => 'nombre', 'note' => 'nota', 'emails' => 'correos', 'keywords' => 'palabras clave',
            'entities' => 'entidades', 'regions' => 'regiones', 'job_keywords' => 'palabras del puesto',
            'job_regions' => 'regiones de empleo', 'job_min_salary' => 'sueldo mínimo',
        ];
    }
}
