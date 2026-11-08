{{-- Columnas por período (ingresos por mes). items: [['label' =>, 'value' =>], ...]; prefix: moneda. --}}
@props(['items', 'prefix' => ''])

@php
    $max = max(1, collect($items)->max('value') ?? 1);
    $last = count($items) - 1;
@endphp

<div {{ $attributes->class(['flex h-36 items-end gap-2']) }} role="img" aria-label="Ingresos por mes">
    @foreach ($items as $i => $item)
        @php
            $height = $item['value'] > 0 ? max(6, round($item['value'] / $max * 100)) : 2;
        @endphp
        <div class="flex h-full flex-1 flex-col items-center justify-end gap-1">
            <span class="text-[10px] font-semibold text-slate-600">{{ $item['value'] > 0 ? $prefix.number_format($item['value'], 0) : '' }}</span>
            <div class="w-full rounded-t-md {{ $i === $last ? 'bg-marca-600' : 'bg-marca-200' }}" style="height: {{ $height }}%" title="{{ $item['label'] }}: {{ $prefix }}{{ number_format($item['value'], 2) }}"></div>
            <span class="text-[10px] text-slate-500">{{ $item['label'] }}</span>
        </div>
    @endforeach
</div>
