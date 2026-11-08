@props(['label', 'value', 'hint' => null, 'tone' => 'default', 'trend' => null, 'href' => null])

@php
    $bar = ['default' => 'bg-marca-600', 'good' => 'bg-emerald-500', 'warn' => 'bg-amber-500', 'bad' => 'bg-red-500', 'muted' => 'bg-slate-400'][$tone] ?? 'bg-marca-600';
    $tag = $href ? 'a' : 'div';
@endphp

<{{ $tag }} @if ($href) href="{{ $href }}" @endif {{ $attributes->class(['relative block overflow-hidden rounded-2xl border border-slate-200 bg-white p-4 shadow-sm', 'transition hover:border-marca-200 hover:shadow' => $href]) }}>
    <span class="absolute inset-y-0 left-0 w-1 {{ $bar }}"></span>
    <div class="text-xs font-medium uppercase tracking-wide text-slate-500">{{ $label }}</div>
    <div class="mt-1 flex items-baseline gap-2">
        <span class="text-2xl font-semibold text-marca-950">{{ $value }}</span>
        @if ($trend !== null)
            <span class="text-xs font-semibold {{ $trend >= 0 ? 'text-emerald-600' : 'text-red-600' }}">{{ $trend >= 0 ? '▲' : '▼' }} {{ abs($trend) }}%</span>
        @endif
    </div>
    @if ($hint) <div class="mt-0.5 text-xs text-slate-500">{{ $hint }}</div> @endif
</{{ $tag }}>
