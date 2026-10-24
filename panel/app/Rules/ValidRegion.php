<?php

namespace App\Rules;

use App\Support\Regions;
use Closure;
use Illuminate\Contracts\Validation\ValidationRule;

class ValidRegion implements ValidationRule
{
    public function validate(string $attribute, mixed $value, Closure $fail): void
    {
        if (! is_string($value) || Regions::canonical($value) === null) {
            $fail("«{$value}» no es una región válida (usa CUSCO o APURIMAC/ABANCAY, como en el SEACE).");
        }
    }
}
