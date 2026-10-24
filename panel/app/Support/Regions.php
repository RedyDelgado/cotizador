<?php

namespace App\Support;

use Illuminate\Support\Str;

/** Departamentos y provincias del SEACE (resources/data/maestras.json, la misma copia que usa el bot). */
class Regions
{
    /** @var array<string, array{name: string, provinces: array<string, string>}>|null */
    private static ?array $index = null;

    public static function normalize(string $text): string
    {
        return mb_strtoupper(Str::ascii(trim(preg_replace('/\s+/', ' ', $text))));
    }

    /** @return array<string, array{name: string, provinces: array<string, string>}> */
    public static function index(): array
    {
        if (self::$index === null) {
            $data = json_decode(file_get_contents(resource_path('data/maestras.json')), true, 512, JSON_THROW_ON_ERROR);
            self::$index = [];
            foreach ($data['departamentos'] as $dep) {
                $provinces = [];
                foreach ($data['provincias'][(string) $dep['id']] ?? [] as $prov) {
                    $provinces[self::normalize($prov['nom'])] = $prov['nom'];
                }
                self::$index[self::normalize($dep['nom'])] = ['name' => $dep['nom'], 'provinces' => $provinces];
            }
        }

        return self::$index;
    }

    /** Para el selector del formulario: [{name, provinces: [..]}, ...]. */
    public static function forForm(): array
    {
        return array_values(array_map(
            fn ($d) => ['name' => $d['name'], 'provinces' => array_values($d['provinces'])],
            self::index()
        ));
    }

    /** "cusco/la convención" -> "CUSCO/LA CONVENCION"; null si no existe. */
    public static function canonical(string $text): ?string
    {
        [$dep, $prov] = array_pad(array_map('trim', explode('/', $text, 2)), 2, '');
        $found = self::index()[self::normalize($dep)] ?? null;
        if (! $found) {
            return null;
        }
        if ($prov === '') {
            return $found['name'];
        }
        $province = $found['provinces'][self::normalize($prov)] ?? null;

        return $province ? $found['name'].'/'.$province : null;
    }
}
