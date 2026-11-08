{{-- Barras horizontales (ranking). items: [['label' =>, 'value' =>], ...] --}}
@props(['items', 'empty' => 'Aún no hay datos.', 'color' => '#7C3AED'])

@php
    $max = max(1, collect($items)->max('value') ?? 1);
@endphp

@if (count($items))
    <ul {{ $attributes->class(['space-y-2.5']) }}>
        @foreach ($items as $item)
            <li>
                <div class="mb-1 flex justify-between gap-2 text-xs">
                    <span class="truncate text-slate-700">{{ $item['label'] }}</span>
                    <b class="text-slate-900">{{ $item['value'] }}</b>
                </div>
                <div class="h-1.5 overflow-hidden rounded-full bg-slate-100">
                    <div class="h-full rounded-full" style="width: {{ round($item['value'] / $max * 100) }}%; background: {{ $color }}"></div>
                </div>
            </li>
        @endforeach
    </ul>
@else
    <p class="text-xs text-slate-500">{{ $empty }}</p>
@endif
