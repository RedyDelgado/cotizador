<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class StorePaymentRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true; // el acceso lo controlan las rutas (sesión o token)
    }

    public function rules(): array
    {
        return [
            'amount' => ['nullable', 'numeric', 'min:0', 'max:100000'],
            'days' => ['nullable', 'integer', 'min:1', 'max:366'],
            'method' => ['required', Rule::in(array_keys(config('panel.payment_methods')))],
            'reference' => ['nullable', 'string', 'max:60'],
            'paid_on' => ['nullable', 'date', 'before_or_equal:today'],
            'note' => ['nullable', 'string', 'max:120'],
        ];
    }

    public function messages(): array
    {
        return [
            'method.required' => 'Elige cómo pagó.',
            'method.in' => 'Ese medio de pago no existe.',
            'paid_on.before_or_equal' => 'La fecha del pago no puede ser futura.',
        ];
    }

    public function attributes(): array
    {
        return ['amount' => 'monto', 'days' => 'días', 'method' => 'medio de pago', 'reference' => 'operación', 'paid_on' => 'fecha'];
    }

    /** Lo que no se llene toma el precio y los días de config/panel.php (S/ 5 por 15 días). */
    public function paymentData(): array
    {
        $data = $this->validated();
        $data['amount'] = $data['amount'] ?? config('panel.price');
        $data['days'] = $data['days'] ?? config('panel.days');

        return $data;
    }
}
