@props(['title' => null, 'subtitle' => null])

<section {{ $attributes->class(['rounded-2xl border border-slate-200 bg-white p-4 shadow-sm']) }}>
    @if ($title)
        <header class="mb-3">
            <h2 class="text-sm font-semibold text-marca-950">{{ $title }}</h2>
            @if ($subtitle) <p class="text-xs text-slate-500">{{ $subtitle }}</p> @endif
        </header>
    @endif
    {{ $slot }}
</section>
