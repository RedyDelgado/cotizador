{{-- Menú desplegable sin JavaScript (details). label: texto del botón; el contenido va en el slot. --}}
@props(['label' => 'Más'])

<details {{ $attributes->class(['relative']) }}>
    <summary class="flex cursor-pointer list-none items-center rounded-lg px-2 py-1 text-sm text-slate-600 marker:hidden hover:bg-marca-50 [&::-webkit-details-marker]:hidden">{{ $label }} ▾</summary>
    <div class="absolute right-0 z-20 mt-1 w-40 rounded-xl border border-slate-200 bg-white p-1 shadow-lg">
        {{ $slot }}
    </div>
</details>
