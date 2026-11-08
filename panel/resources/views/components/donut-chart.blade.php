{{-- Dona SVG. segments: [['label' =>, 'value' =>, 'color' =>], ...]; center: texto grande en el centro. --}}
@props(['segments', 'center' => null, 'caption' => null])

@php
    $total = collect($segments)->sum('value');
    $radius = 40;
    $circumference = 2 * M_PI * $radius;
    $offset = 0;
@endphp

<div {{ $attributes->class(['flex items-center gap-4']) }}>
    <svg viewBox="0 0 100 100" class="h-28 w-28 flex-none -rotate-90" role="img" aria-label="{{ $caption }}">
        <circle cx="50" cy="50" r="{{ $radius }}" fill="none" stroke="#E2E8F0" stroke-width="14"/>
        @if ($total > 0)
            @foreach ($segments as $segment)
                @php
                    $length = $segment['value'] / $total * $circumference;
                @endphp
                @if ($segment['value'] > 0)
                    <circle cx="50" cy="50" r="{{ $radius }}" fill="none" stroke="{{ $segment['color'] }}" stroke-width="14"
                            stroke-dasharray="{{ round($length, 2) }} {{ round($circumference - $length, 2) }}" stroke-dashoffset="{{ round(-$offset, 2) }}"/>
                    @php
                        $offset += $length;
                    @endphp
                @endif
            @endforeach
        @endif
        <text x="50" y="50" transform="rotate(90 50 50)" text-anchor="middle" dominant-baseline="central" class="fill-marca-950 text-[18px] font-semibold">{{ $center ?? $total }}</text>
    </svg>
    <ul class="min-w-0 flex-1 space-y-1.5 text-xs">
        @foreach ($segments as $segment)
            <li class="flex items-center gap-2">
                <span class="h-2.5 w-2.5 flex-none rounded-full" style="background: {{ $segment['color'] }}"></span>
                <span class="flex-1 truncate text-slate-600">{{ $segment['label'] }}</span>
                <b class="text-slate-900">{{ $segment['value'] }}</b>
            </li>
        @endforeach
    </ul>
</div>
